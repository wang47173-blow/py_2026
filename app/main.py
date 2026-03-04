from __future__ import annotations

import asyncio
from uuid import UUID

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest

from app.config import settings
from app.db import ping_db
from app.ingestion import create_index_job, get_job_status, init_schema, run_index_job
from app.logging import setup_logging
from app.mcp_skeleton import PROMPTS, RESOURCES, TOOLS
from app.schemas import IndexDocsRequest, IndexDocsResponse, JobStatusResponse

setup_logging(settings.log_level)

app = FastAPI(title=settings.app_name)
REQUEST_COUNTER = Counter("eka_http_requests_total", "Total HTTP requests", ["path"])


@app.on_event("startup")
async def startup_event() -> None:
    await init_schema()


@app.middleware("http")
async def count_requests(request, call_next):
    REQUEST_COUNTER.labels(path=request.url.path).inc()
    return await call_next(request)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz")
async def readyz() -> JSONResponse:
    ready = await ping_db()
    if ready:
        return JSONResponse(status_code=200, content={"status": "ready"})
    return JSONResponse(status_code=503, content={"status": "not_ready", "reason": "db_unreachable"})


@app.get("/metrics")
async def metrics() -> PlainTextResponse:
    return PlainTextResponse(generate_latest().decode("utf-8"), media_type=CONTENT_TYPE_LATEST)


@app.get("/mcp/tools")
async def mcp_tools():
    return {"tools": TOOLS}


@app.get("/mcp/resources")
async def mcp_resources():
    return {"resources": RESOURCES}


@app.get("/mcp/prompts")
async def mcp_prompts():
    return {"prompts": PROMPTS}


@app.post("/mcp/tools/index_docs", response_model=IndexDocsResponse)
async def index_docs(payload: IndexDocsRequest) -> IndexDocsResponse:
    job_id = await create_index_job(
        data_source=payload.data_source,
        tenant_id=payload.tenant_id,
        visibility_policy=payload.visibility_policy,
        tags=payload.tags,
        idempotency_key=payload.idempotency_key,
    )
    asyncio.create_task(run_index_job(job_id))
    return IndexDocsResponse(job_id=job_id)


@app.get("/mcp/tools/index_docs/{job_id}", response_model=JobStatusResponse)
async def index_docs_status(job_id: UUID) -> JobStatusResponse:
    status = await get_job_status(job_id)
    if not status:
        raise HTTPException(status_code=404, detail="job not found")
    return JobStatusResponse(**status)
