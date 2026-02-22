"""
LangGraph ReAct Agent for PostgreSQL Observability.

Integrates with open-source MCP servers (Prometheus + VictoriaLogs)
via stdio transport, using LangGraph for agentic reasoning and Langfuse
for LLM tracing.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from contextlib import AsyncExitStack
from typing import Any, Dict, List, Optional, Sequence, TypedDict, Annotated

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.tools import tool as langchain_tool, StructuredTool
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langfuse.callback import CallbackHandler as LangfuseCallbackHandler

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from config import get_settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Agent State
# ---------------------------------------------------------------------------

class AgentState(TypedDict):
    """State for the LangGraph agent."""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    database: str
    db_type: str


# ---------------------------------------------------------------------------
# System Prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT_TEMPLATE = """You are a PostgreSQL observability expert. You have access to Prometheus metrics and VictoriaLogs log data for the PostgreSQL database named `{database}` (DB Type: `{db_type}`).

You must NEVER attempt to connect directly to the database. All data must be fetched exclusively through your available tools.

You have two categories of tools:
1. **Prometheus tools** — for querying PostgreSQL metrics (PromQL). Use these for numeric time-series data like connection counts, replication lag, cache hit ratios, etc.
2. **VictoriaLogs tools** — for querying PostgreSQL logs (LogsQL). Use these for log analysis, error investigation, query patterns, and event correlation.

When diagnosing issues, always correlate metrics with logs. Provide clear, structured, actionable insights. When you find anomalies, explain what they mean and suggest remediation steps.

Key PostgreSQL metrics you can investigate via Prometheus:
- Connections: pg_stat_activity, connection counts, connection pool usage
- Replication: replication lag, WAL generation rate
- Performance: cache hit ratio, transaction rate, query execution times
- Locks: lock counts, deadlocks, blocking queries
- Storage: table/index bloat, disk usage, tablespace sizes
- Autovacuum: vacuum activity, dead tuples, table stats

Key PostgreSQL logs you can investigate via VictoriaLogs:
- Error logs: FATAL, ERROR, PANIC messages
- Slow query logs: queries exceeding duration thresholds
- Connection events: connection attempts, authentication failures
- Checkpoint and WAL activity
- Autovacuum and maintenance events
- Replication-related log entries

When using Prometheus tools, construct PromQL queries filtering by the database instance and db_type. Your queries MUST include the labels `job="{database}"` and `db_type="{db_type}"`.
When using VictoriaLogs tools, use LogsQL queries to search and analyze log entries.

Always provide:
1. A clear summary of findings
2. Relevant metric values and log evidence with context
3. Actionable recommendations when issues are found
"""


def build_system_prompt(database: str, db_type: str) -> str:
    """Build the system prompt with the database name and db type injected."""
    return SYSTEM_PROMPT_TEMPLATE.format(database=database, db_type=db_type)


# ---------------------------------------------------------------------------
# MCP Client Manager
# ---------------------------------------------------------------------------

class MCPClientManager:
    """Manages connections to MCP servers via stdio transport."""

    def __init__(self):
        self._exit_stack = AsyncExitStack()
        self._sessions: Dict[str, ClientSession] = {}
        self._tools: List[StructuredTool] = []
        self._initialized = False

    async def initialize(self):
        """Start MCP server subprocesses and discover tools."""
        if self._initialized:
            return

        settings = get_settings()

        # --- Prometheus MCP Server ---
        try:
            prom_params = StdioServerParameters(
                command="docker",
                args=[
                    "run", "-i", "--rm",
                    "-e", "PROMETHEUS_URL",
                    "ghcr.io/pab1it0/prometheus-mcp-server:latest",
                ],
                env={
                    **os.environ,
                    "PROMETHEUS_URL": settings.prometheus_url,
                },
            )
            prom_transport = await self._exit_stack.enter_async_context(
                stdio_client(prom_params)
            )
            prom_read, prom_write = prom_transport
            prom_session = await self._exit_stack.enter_async_context(
                ClientSession(prom_read, prom_write)
            )
            await prom_session.initialize()
            self._sessions["prometheus"] = prom_session
            logger.info("✅ Prometheus MCP server connected")
        except Exception as e:
            logger.warning(f"⚠️  Prometheus MCP server failed to start: {e}")

        # --- VictoriaLogs MCP Server ---
        try:
            vl_params = StdioServerParameters(
                command="docker",
                args=[
                    "run", "-i", "--rm",
                    "-e", "VL_INSTANCE_ENTRYPOINT",
                    "-e", "MCP_SERVER_MODE",
                    "ghcr.io/victoriametrics-community/mcp-victorialogs",
                ],
                env={
                    **os.environ,
                    "VL_INSTANCE_ENTRYPOINT": settings.victoria_logs_url,
                    "MCP_SERVER_MODE": "stdio",
                },
            )
            vl_transport = await self._exit_stack.enter_async_context(
                stdio_client(vl_params)
            )
            vl_read, vl_write = vl_transport
            vl_session = await self._exit_stack.enter_async_context(
                ClientSession(vl_read, vl_write)
            )
            await vl_session.initialize()
            self._sessions["victorialogs"] = vl_session
            logger.info("✅ VictoriaLogs MCP server connected")
        except Exception as e:
            logger.warning(f"⚠️  VictoriaLogs MCP server failed to start: {e}")

        # Discover and register tools from all connected MCP servers
        await self._discover_tools()
        self._initialized = True

    async def _discover_tools(self):
        """Discover tools from all connected MCP sessions and wrap them as LangChain tools."""
        self._tools = []

        for server_name, session in self._sessions.items():
            try:
                tools_response = await session.list_tools()
                for mcp_tool in tools_response.tools:
                    lc_tool = self._wrap_mcp_tool(server_name, session, mcp_tool)
                    self._tools.append(lc_tool)
                    logger.info(f"  📦 Registered tool: {mcp_tool.name} (from {server_name})")
            except Exception as e:
                logger.warning(f"Failed to list tools from {server_name}: {e}")

    def _wrap_mcp_tool(self, server_name: str, session: ClientSession, mcp_tool) -> StructuredTool:
        """Wrap an MCP tool as a LangChain StructuredTool."""
        tool_name = f"{server_name}__{mcp_tool.name}"
        tool_description = mcp_tool.description or f"Tool '{mcp_tool.name}' from {server_name} MCP server"

        # Build the JSON schema for input
        input_schema = mcp_tool.inputSchema if mcp_tool.inputSchema else {"type": "object", "properties": {}}

        async def _invoke_tool(**kwargs) -> str:
            """Call the MCP tool and return the result."""
            try:
                result = await session.call_tool(mcp_tool.name, arguments=kwargs)
                # Extract text content from the result
                if result.content:
                    parts = []
                    for block in result.content:
                        if hasattr(block, "text"):
                            parts.append(block.text)
                        else:
                            parts.append(str(block))
                    return "\n".join(parts)
                return "No results returned."
            except Exception as e:
                return f"Error calling tool {mcp_tool.name}: {str(e)}"

        return StructuredTool.from_function(
            func=None,
            coroutine=_invoke_tool,
            name=tool_name,
            description=f"[{server_name}] {tool_description}",
            args_schema=None,
            infer_schema=False,
            args_schema_json=input_schema,
        )

    @property
    def tools(self) -> List[StructuredTool]:
        return self._tools

    async def cleanup(self):
        """Clean up all MCP connections."""
        await self._exit_stack.aclose()
        self._initialized = False


# ---------------------------------------------------------------------------
# LLM Factory
# ---------------------------------------------------------------------------

def create_llm(callback_handler: Optional[Any] = None):
    """Create the LLM instance based on settings."""
    settings = get_settings()
    callbacks = [callback_handler] if callback_handler else []

    if settings.llm_provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model=settings.llm_model or "claude-3-5-sonnet-20240620",
            api_key=settings.anthropic_api_key,
            callbacks=callbacks,
            max_tokens=4096,
        )
    elif settings.llm_provider == "litellm":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=settings.litellm_model,
            api_key=settings.litellm_api_key,
            base_url=settings.litellm_url,
            callbacks=callbacks,
            streaming=True,
        )
    else:
        # Default to OpenAI
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=settings.llm_model or "gpt-4o",
            api_key=settings.openai_api_key,
            callbacks=callbacks,
        )


# ---------------------------------------------------------------------------
# Langfuse Callback
# ---------------------------------------------------------------------------

def create_langfuse_handler(database: str, conversation_id: str) -> Optional[LangfuseCallbackHandler]:
    """Create a Langfuse callback handler for tracing."""
    settings = get_settings()
    if not settings.langfuse_public_key or not settings.langfuse_secret_key:
        logger.info("Langfuse keys not set — tracing disabled.")
        return None
    try:
        return LangfuseCallbackHandler(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
            session_id=conversation_id,
            metadata={"database": database, "db_type": kwargs.get("db_type")},
            tags=["postgres-observability", database],
        )
    except Exception as e:
        logger.warning(f"Failed to create Langfuse handler: {e}")
        return None


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------

# Global MCP client (singleton)
mcp_manager = MCPClientManager()


async def ensure_mcp_initialized():
    """Initialize MCP connections if not already done."""
    await mcp_manager.initialize()


def build_graph(tools: List[StructuredTool]):
    """Build the LangGraph StateGraph with a ReAct loop."""
    settings = get_settings()

    # --- Nodes ---
    async def agent_node(state: AgentState) -> dict:
        """Call the LLM with the current messages and available tools."""
        database = state["database"]
        db_type = state["db_type"]
        langfuse_handler = create_langfuse_handler(
            database=database,
            conversation_id="default",
            db_type=db_type,
        )
        llm = create_llm(callback_handler=langfuse_handler)
        llm_with_tools = llm.bind_tools(tools)

        messages = list(state["messages"])

        # Ensure system prompt is the first message
        if not messages or not isinstance(messages[0], SystemMessage):
            messages.insert(0, SystemMessage(content=build_system_prompt(database, db_type)))
        else:
            messages[0] = SystemMessage(content=build_system_prompt(database, db_type))

        response = await llm_with_tools.ainvoke(messages)
        return {"messages": [response]}

    tool_node = ToolNode(tools)

    # --- Routing ---
    def should_continue(state: AgentState) -> str:
        """Determine if the agent should continue or stop."""
        last_message = state["messages"][-1]
        if isinstance(last_message, AIMessage) and last_message.tool_calls:
            return "tools"
        return END

    # --- Build Graph ---
    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tool_node)
    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")

    return graph.compile()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def run_agent(
    message: str,
    database: str,
    db_type: str,
    conversation_id: str,
    history: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """
    Run the observability agent for a user message.

    Returns:
        {
            "response": str,
            "tool_calls": [ { "tool": str, "args": dict, "result": str }, ... ]
        }
    """
    await ensure_mcp_initialized()

    tools = mcp_manager.tools
    compiled_graph = build_graph(tools)

    # Build message history
    messages: List[BaseMessage] = []
    if history:
        for msg in history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "user":
                messages.append(HumanMessage(content=content))
            elif role == "assistant":
                messages.append(AIMessage(content=content))

    messages.append(HumanMessage(content=message))

    # Create Langfuse handler
    langfuse_handler = create_langfuse_handler(database, conversation_id, db_type=db_type)
    config = {}
    if langfuse_handler:
        config["callbacks"] = [langfuse_handler]

    # Run the graph
    initial_state: AgentState = {
        "messages": messages,
        "database": database,
        "db_type": db_type,
    }

    result = await compiled_graph.ainvoke(initial_state, config=config)

    # Extract the final response and tool calls
    final_messages = result["messages"]
    response_text = ""
    tool_calls_info = []

    for msg in final_messages:
        if isinstance(msg, AIMessage):
            if msg.content and not msg.tool_calls:
                response_text = msg.content
            if msg.tool_calls:
                for tc in msg.tool_calls:
                    tool_calls_info.append({
                        "tool": tc["name"],
                        "args": tc["args"],
                        "result": "",  # will be filled from ToolMessage
                    })
        elif isinstance(msg, ToolMessage):
            # Match to the last tool call without a result
            for tc_info in tool_calls_info:
                if not tc_info["result"]:
                    tc_info["result"] = msg.content[:500] if msg.content else ""
                    break

    if not response_text:
        # Fallback: grab the last AI message content
        for msg in reversed(final_messages):
            if isinstance(msg, AIMessage) and msg.content:
                response_text = msg.content
                break

    return {
        "response": response_text or "I was unable to generate a response. Please try again.",
        "tool_calls": tool_calls_info,
    }


