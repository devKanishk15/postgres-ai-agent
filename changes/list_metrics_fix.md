# list_metrics Fix - 2026-02-21

## Issue
Prometheus MCP Server returned a `ValidationError` when calling `list_metrics`. The agent was using `match[]` instead of the expected `filter_pattern`.

## Resolution
- Inspected the tool schema using a custom script.
- Updated `SYSTEM_PROMPT_TEMPLATE` in `backend/agent.py` to specify the use of `filter_pattern`.
- Restarted the `backend` container to apply changes.

## Verification
- Container successfully restarted.
- Agent system prompt updated.
