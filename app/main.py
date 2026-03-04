from __future__ import annotations

import asyncio
from uuid import UUID

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

from app.config import settings
from app.db import ping_db
from app.ingestion import create_index_job, get_job_status, init_schema, run_index_job
from app.logging import setup_logging
from app.mcp_skeleton import PROMPTS, RESOURCES, TOOLS
from app.rag import list_corpora, rag_query
from app.rate_limit import allow_request
from app.schemas import (
    IndexDocsRequest,
    IndexDocsResponse,
    JobStatusResponse,
    ListCorporaResponse,
    RagQueryRequest,
    RagQueryResponse,
)

setup_logging(settings.log_level)

app = FastAPI(title=settings.app_name)
REQUEST_COUNTER = Counter("eka_http_requests_total", "Total HTTP requests", ["path", "status"])
RAG_LATENCY = Histogram("eka_rag_latency_ms", "RAG latency ms", buckets=(50, 100, 300, 800, 1500, 3000, 8000))


@app.on_event("startup")
async def startup_event() -> None:
    await init_schema()


@app.middleware("http")
async def middleware(request: Request, call_next):
    identity = request.headers.get("x-user-id", "anonymous")
    if not allow_request(identity):
        return JSONResponse(status_code=429, content={"detail": "rate limit exceeded"})
    response = await call_next(request)
    REQUEST_COUNTER.labels(path=request.url.path, status=str(response.status_code)).inc()
    return response


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


@app.post("/mcp/tools/rag_query", response_model=RagQueryResponse)
async def mcp_rag_query(payload: RagQueryRequest) -> RagQueryResponse:
    try:
        res = await asyncio.wait_for(
            rag_query(
                question=payload.question,
                tenant_id=str(payload.tenant_id),
                user_id=str(payload.user_id),
                top_k=min(payload.top_k, settings.max_top_k),
                filters=payload.filters,
            ),
            timeout=settings.query_timeout_s,
        )
        RAG_LATENCY.observe(res["latency_ms"])
        return RagQueryResponse(**res)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except TimeoutError as exc:
        raise HTTPException(status_code=408, detail="rag query timeout") from exc


@app.get("/mcp/tools/list_corpora/{tenant_id}", response_model=ListCorporaResponse)
async def mcp_list_corpora(tenant_id: UUID) -> ListCorporaResponse:
    res = await list_corpora(str(tenant_id))
    return ListCorporaResponse(**res)


@app.get("/tenants/{tenant_id}/docs", response_model=ListCorporaResponse)
async def resource_docs(tenant_id: UUID) -> ListCorporaResponse:
    res = await list_corpora(str(tenant_id))
    return ListCorporaResponse(**res)


@app.get("/tenants/{tenant_id}/stats")
async def resource_stats(tenant_id: UUID) -> dict:
    res = await list_corpora(str(tenant_id))
    return {"stats": res["stats"]}
