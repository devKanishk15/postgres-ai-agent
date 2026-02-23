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
    level=logging.DEBUG,
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


class JobsResponse(BaseModel):
    jobs: List[str]


class DbTypesResponse(BaseModel):
    db_types: List[str]


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


async def fetch_prometheus_jobs() -> List[str]:
    """
    Query Prometheus pg_up metric and return all unique job label values.
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
        return []

    results = data.get("data", {}).get("result", [])
    jobs = set()
    for item in results:
        job = item.get("metric", {}).get("job", "")
        if job:
            jobs.add(job)
    return sorted(jobs)


async def fetch_db_types_for_job(job_name: str) -> List[str]:
    """
    Query Prometheus pg_up metric filtered by job and return unique db_type
    label values. Returns empty list if db_type label is not present.
    """
    settings = get_settings()
    prometheus_url = settings.prometheus_url

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{prometheus_url}/api/v1/query",
                params={"query": f'pg_up{{job="{job_name}"}}'},
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        logger.warning(f"Failed to query Prometheus for db_types: {e}")
        return []

    results = data.get("data", {}).get("result", [])
    db_types = set()
    for item in results:
        db_type = item.get("metric", {}).get("db_type", "")
        if db_type:
            db_types.add(db_type)
    return sorted(db_types)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    logger.debug("Health check requested")
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


@app.get("/jobs", response_model=JobsResponse)
async def list_jobs():
    """Return all unique Prometheus job names from the pg_up metric."""
    logger.info("📋 Fetching Prometheus jobs...")
    jobs = await fetch_prometheus_jobs()
    logger.info(f"📋 Found {len(jobs)} jobs: {jobs}")
    return JobsResponse(jobs=jobs)


@app.get("/jobs/{job_name}/db_types", response_model=DbTypesResponse)
async def list_db_types(job_name: str):
    """Return unique db_type label values for a given Prometheus job."""
    logger.info(f"🔍 Fetching db_types for job='{job_name}'...")
    db_types = await fetch_db_types_for_job(job_name)
    logger.info(f"🔍 Found db_types for '{job_name}': {db_types}")
    return DbTypesResponse(db_types=db_types)


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Send a message to the observability agent."""
    logger.info(f"💬 /chat request — database='{request.database}', db_type='{request.db_type}', conv='{request.conversation_id}', history_len={len(request.history) if request.history else 0}")
    logger.info(f"💬 User message: {request.message[:300]}")

    if not request.message.strip():
        logger.warning("❌ Empty message received")
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    if not request.database.strip():
        logger.warning("❌ No database specified")
        raise HTTPException(status_code=400, detail="Database (job name) is required")

    conversation_id = request.conversation_id or str(uuid.uuid4())

    history = []
    if request.history:
        history = [{"role": h.role, "content": h.content} for h in request.history]

    try:
        logger.info(f"⏳ Invoking agent for conv='{conversation_id}'...")
        result = await run_agent(
            message=request.message,
            database=request.database,
            db_type=request.db_type,
            conversation_id=conversation_id,
            history=history,
        )
        logger.info(f"✅ Agent returned — response_len={len(result.get('response', ''))}, tool_calls={len(result.get('tool_calls', []))}")
        for i, tc in enumerate(result.get('tool_calls', [])):
            logger.info(f"   Tool[{i}]: {tc['tool']} — result_len={len(tc.get('result', ''))}")
    except Exception as e:
        logger.exception("❌ Agent invocation failed")
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
