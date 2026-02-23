# MCP Tool Argument Filtering Fix - 2026-02-21

## Issue
Multiple MCP tools (`list_metrics`, `get_targets`) threw `ValidationError: Unexpected keyword argument`
because the LLM hallucinated invalid arguments (e.g. `match[]`) or passed empty `{}` to no-argument tools.

## Root Cause
`_invoke_tool(**kwargs)` in `agent.py` forwarded **all** LLM-generated kwargs directly to `session.call_tool()`,
with no filtering against the tool's declared input schema.

## Fix
Added argument filtering in `_invoke_tool` (line ~197 of `backend/agent.py`):

```python
schema_props = input_schema.get("properties", {})
filtered_args = {k: v for k, v in kwargs.items() if k in schema_props}
result = await session.call_tool(mcp_tool.name, arguments=filtered_args)
```

This drops any keyword arguments not declared in the tool's JSON schema before forwarding to the MCP server.
