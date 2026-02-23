# VictoriaLogs db_type Filter + Logging + Tool Fix

**Date:** 2026-02-23

## Changes Made

### 1. System Prompt — `db_type` Label Filtering (`agent.py`)
- LLM now always includes `db_type:"{db_type}"` in every LogsQL query
- Added example LogsQL query patterns with the `db_type` filter

### 2. Bug Fix — Empty Tool Arguments (`agent.py`) ⚠️ Critical
- `_invoke_tool` was filtering kwargs against MCP tool schema, but LangGraph's `ToolNode` passes args differently
- All arguments were dropped to `{}`, causing every MCP tool to receive no query → returned "No results returned."
- Agent looped 6+ times then gave up
- **Fix:** Removed broken filter, now passes all kwargs directly to MCP server

### 3. Bug Fix — `create_langfuse_handler` (`agent.py`)
- Referenced undefined `kwargs`; now uses explicit `db_type` parameter

### 4. Detailed Logging — Backend (`agent.py`, `main.py`)
- Tool invocations: raw kwargs, args sent, result length, errors with stack traces
- LLM calls, graph routing decisions, `run_agent` lifecycle
- All endpoints logged, log level set to DEBUG

### 5. Detailed Logging — Frontend (`api.ts`, `page.tsx`)
- All API calls with request/response logging (`[API]` prefix in console)
- User action logging: database/db_type selection, message send/receive (`[UI]` prefix)

## Verification

**Before fix:**
```
🔧 Calling tool 'query' with args: {}          ← EMPTY
✅ Tool 'query' returned 23 chars               ← "No results returned."
```

**After fix:**
```
🔧 raw kwargs keys: ['query', 'start', 'end', 'limit']
🔧 Calling tool 'query' with args: {"query": "db_type:\"master\" AND _msg:\"ERROR\"", ...}
✅ Tool 'query' returned real data
🏁 run_agent finished — response_len=1880, tool_calls=17
```
