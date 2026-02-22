"""
FastAPI backend for the PostgreSQL Observability Agent.

Endpoints:
  POST /chat                  — Send a message to the agent
  GET  /databases             — List available databases (with job field)
  GET  /databases/{name}/job  — Auto-detect Prometheus job for a database
  GET  /health                — Health check
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, List, Optional

import httpx
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
    description="AI-powered PostgreSQL monitoring via Prometheus & VictoriaLogs MCP servers",
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
    db_type: str
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
    job: Optional[str] = None


class DatabasesResponse(BaseModel):
    databases: List[DatabaseItem]


class JobDetectionResponse(BaseModel):
    database: str
    job: Optional[str]
    instance: Optional[str]
    source: str  # "config" | "prometheus" | "not_found"


class HealthResponse(BaseModel):
    status: str


# ---------------------------------------------------------------------------
# Prometheus Job Detection Helper
# ---------------------------------------------------------------------------

async def detect_job_from_prometheus(db_name: str) -> Dict[str, Optional[str]]:
    """
    Query Prometheus pg_up metric and attempt to find the job label
    associated with the given database name.

    Strategy:
    1. Query pg_up to get all active instances with their labels.
    2. Try to match the instance label against the db_name (substring match).
    3. If no match, return all unique jobs found (first one wins as best-effort).

    Returns: {"job": str | None, "instance": str | None}
    """
    settings = get_settings()
    prometheus_url = settings.prometheus_url

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{prometheus_url}/api/v1/query",
                params={"query": "pg_up"},
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        logger.warning(f"Failed to query Prometheus for pg_up: {e}")
        return {"job": None, "instance": None}

    results = data.get("data", {}).get("result", [])
    if not results:
        logger.info("pg_up returned no results from Prometheus")
        return {"job": None, "instance": None}

    # Try exact / substring match on instance label vs db_name
    for item in results:
        metric = item.get("metric", {})
        instance = metric.get("instance", "")
        job = metric.get("job", "")
        # Match if the db name appears in the instance string (hostname part)
        if db_name.lower() in instance.lower():
            logger.info(f"Matched db '{db_name}' → job='{job}', instance='{instance}' (name match)")
            return {"job": job or None, "instance": instance or None}

    # No name match — return the first unique job as a best-effort fallback
    first = results[0].get("metric", {})
    job = first.get("job") or None
    instance = first.get("instance") or None
    logger.info(f"No name match for '{db_name}'; returning first pg_up job='{job}', instance='{instance}'")
    return {"job": job, "instance": instance}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(status="ok")


@app.get("/databases", response_model=DatabasesResponse)
async def list_databases():
    """Return all available databases from config, including their configured job."""
    dbs = get_databases()
    return DatabasesResponse(
        databases=[
            DatabaseItem(name=db.name, job=db.job)
            for db in dbs
        ]
    )


@app.get("/databases/{name}/job", response_model=JobDetectionResponse)
async def get_database_job(name: str):
    """
    Return the Prometheus job name for a given database.

    Resolution order:
    1. If the database entry in databases.yaml has a `job` field set → return it directly.
    2. Otherwise, query Prometheus pg_up and auto-detect the job from metric labels.
    """
    # Validate database exists
    db_map = {db.name: db for db in get_databases()}
    if name not in db_map:
        raise HTTPException(status_code=404, detail=f"Unknown database: {name}")

    db_entry = db_map[name]

    # 1. Config-defined job takes priority
    if db_entry.job:
        logger.info(f"Job for '{name}' resolved from config: {db_entry.job}")
        return JobDetectionResponse(
            database=name,
            job=db_entry.job,
            instance=None,
            source="config",
        )

    # 2. Auto-detect from Prometheus pg_up
    detected = await detect_job_from_prometheus(name)
    if detected["job"]:
        return JobDetectionResponse(
            database=name,
            job=detected["job"],
            instance=detected["instance"],
            source="prometheus",
        )

    # 3. Nothing found
    return JobDetectionResponse(
        database=name,
        job=None,
        instance=None,
        source="not_found",
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
            db_type=request.db_type,
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
