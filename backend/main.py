"""
FastAPI backend for the PostgreSQL Observability Agent.

Endpoints:
  POST /chat       — Send a message to the agent
  GET  /databases  — List available databases
  GET  /health     — Health check
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import get_databases, get_settings
from agent import run_agent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# FastAPI App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="PostgreSQL Observability Agent",
    description="AI-powered PostgreSQL monitoring via Prometheus & VictoriaMetrics MCP servers",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request / Response Models
# ---------------------------------------------------------------------------

class HistoryMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    database: str
    conversation_id: Optional[str] = None
    history: Optional[List[HistoryMessage]] = None


class ToolCallInfo(BaseModel):
    tool: str
    args: Dict[str, Any]
    result: str


class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    tool_calls: List[ToolCallInfo]


class DatabaseItem(BaseModel):
    name: str
    label: str


class DatabasesResponse(BaseModel):
    databases: List[DatabaseItem]


class HealthResponse(BaseModel):
    status: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(status="ok")


@app.get("/databases", response_model=DatabasesResponse)
async def list_databases():
    """Return all available databases from config."""
    dbs = get_databases()
    return DatabasesResponse(
        databases=[DatabaseItem(name=db.name, label=db.label) for db in dbs]
    )


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Send a message to the observability agent."""
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    # Validate database exists
    valid_names = {db.name for db in get_databases()}
    if request.database not in valid_names:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown database: {request.database}",
        )

    conversation_id = request.conversation_id or str(uuid.uuid4())

    history = []
    if request.history:
        history = [{"role": h.role, "content": h.content} for h in request.history]

    try:
        result = await run_agent(
            message=request.message,
            database=request.database,
            conversation_id=conversation_id,
            history=history,
        )
    except Exception as e:
        logger.exception("Agent invocation failed")
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")

    return ChatResponse(
        response=result["response"],
        conversation_id=conversation_id,
        tool_calls=[
            ToolCallInfo(
                tool=tc["tool"],
                args=tc["args"],
                result=tc["result"],
            )
            for tc in result.get("tool_calls", [])
        ],
    )


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
