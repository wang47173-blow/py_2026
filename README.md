# Enterprise Knowledge Assistant Gateway (M0)

M0 delivers a runnable foundation for an enterprise RAG + MCP system:
- FastAPI app skeleton
- MCP surface skeleton (`/mcp/tools`, `/mcp/resources`, `/mcp/prompts`)
- Health endpoints (`/healthz`, `/readyz`)
- PostgreSQL + pgvector via Docker Compose
- Prometheus metrics endpoint (`/metrics`)

## Quick start

```bash
docker compose up --build
```

Then verify:

```bash
curl http://localhost:8080/healthz
curl http://localhost:8080/readyz
curl http://localhost:8080/mcp/tools
curl http://localhost:8080/metrics
```

## Local tests

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt pytest
pytest -q
```

## What comes in M1+
- Real `index_docs` ingestion pipeline
- ACL-aware retrieval
- `rag_query` with citations and audit logs
- evaluation dataset and scripts
