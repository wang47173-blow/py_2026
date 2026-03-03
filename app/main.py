from fastapi import FastAPI
from fastapi.responses import PlainTextResponse, JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest

from app.config import settings
from app.db import ping_db
from app.logging import setup_logging
from app.mcp_skeleton import PROMPTS, RESOURCES, TOOLS

setup_logging(settings.log_level)

app = FastAPI(title=settings.app_name)

REQUEST_COUNTER = Counter("eka_http_requests_total", "Total HTTP requests", ["path"]) 


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
