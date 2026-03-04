# Enterprise Knowledge Assistant Gateway (M1)

M1 delivers a runnable ingestion MVP for an enterprise RAG + MCP system:
- FastAPI app skeleton
- MCP endpoints for tool/resource/prompt descriptors
- `index_docs` ingestion tool endpoint + async job status endpoint
- md/txt local-folder ingestion, chunking, placeholder embedding, DB persistence
- Health endpoints (`/healthz`, `/readyz`)
- PostgreSQL + pgvector via Docker Compose
- Prometheus metrics endpoint (`/metrics`)

## Quick start (Docker)

```bash
docker compose up --build
```

### In another terminal, verify health

```bash
curl http://localhost:8080/healthz
curl http://localhost:8080/readyz
```

### Run M1 ingestion

```bash
mkdir -p data
cat > data/handbook.md <<'EOF'
# Employee Handbook
All employees must follow security best practices.
EOF

curl -X POST http://localhost:8080/mcp/tools/index_docs \
  -H 'Content-Type: application/json' \
  -d '{
    "data_source": "data",
    "tenant_id": "11111111-1111-1111-1111-111111111111",
    "visibility_policy": {"scope": "internal"},
    "tags": ["hr", "policy"],
    "idempotency_key": "demo-data-v1"
  }'
```

Query job status:

```bash
curl http://localhost:8080/mcp/tools/index_docs/<job_id>
```

## Local tests

```bash
conda activate s_env
pip install -r requirements.txt pytest
pytest -q
```

## What comes in M2+
- ACL-aware retrieval and `rag_query`
- citation formatting
- audit logging and evaluation scripts
