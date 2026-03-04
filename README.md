# Enterprise Knowledge Assistant Gateway (Final mode)

This version includes M0~M5 essentials:
- MCP tool/resource/prompt surface
- Ingestion (`index_docs`) with idempotency and job status
- Retrieval + tenant and ACL policy filtering (pgvector index + SQL pushdown)
- Generation with Fireworks GLM-5 (LangChain) + citations
- Guardrails for prompt-injection patterns + refusal behavior
- Audit logs (`query_logs`, `query_chunk_access`)
- Rate limit + timeout + top_k/context budget controls
- Metrics endpoint + Prometheus + OpenTelemetry tracing (OTLP -> Jaeger)
- Eval suite with 20-sample golden dataset

## 1) Configure `.env`

```bash
cp .env.example .env
```

Fill only your local key:

```env
EKA_FIREWORKS_API_KEY=
```

## 2) Start stack

```bash
docker compose up --build
```

## 3) Health checks

```bash
curl http://localhost:8080/healthz
curl http://localhost:8080/readyz
curl http://localhost:8080/metrics
curl http://localhost:8080/mcp/tools
```

## 4) Index sample data

```bash
mkdir -p data
cat > data/handbook.md <<'EOF'
# Employee Handbook
All employees must follow security best practices and compliance requirements.
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

Then poll:

```bash
curl http://localhost:8080/mcp/tools/index_docs/<job_id>
```

## 5) Query RAG

```bash
curl -X POST http://localhost:8080/mcp/tools/rag_query \
  -H 'Content-Type: application/json' \
  -H 'x-user-id: 22222222-2222-2222-2222-222222222222' \
  -d '{
    "question": "What does the handbook say about security?",
    "tenant_id": "11111111-1111-1111-1111-111111111111",
    "user_id": "22222222-2222-2222-2222-222222222222",
    "top_k": 3,
    "filters": {}
  }'
```

## 6) Eval (20 golden samples)

```bash
python eval/run_eval.py
```

Expected output shape:

```json
{
  "hit_rate": 0.7,
  "citation_coverage": 0.9,
  "refusal_rate": 1.0,
  "avg_latency_ms": 800,
  "samples": 20
}
```

## ACL model notes

- ACL table: `acl_policies` with `allow/deny` and `user/group/all` subjects.
- Retrieval enforces tenant + ACL before ranking.
- `deny` rule overrides allow.

## Conda local run (`s_env`)

```bash
conda activate s_env
pip install -r requirements.txt pytest
uvicorn app.main:app --host 0.0.0.0 --port 8080
```


## 7) Optional: open Jaeger UI

```bash
open http://localhost:16686
```

## Enterprise-readiness note

This repo now covers end-to-end runnable baseline for interviews. For production, migrate in-memory rate-limit to Redis and move schema DDL to Alembic migrations.


## Developer workflow

```bash
make install
make lint
make test-fast
```

## Security defaults

- `index_docs` data source is restricted under `EKA_INGEST_DATA_ROOT`.
- Ingestion retries are configurable via `EKA_INGEST_MAX_RETRIES`.
- Keep `.env` local only; never commit keys.


## Schema migrations (Alembic)

```bash
alembic upgrade head
```

The app also runs migrations on startup before serving traffic.


## Rate limiting backend

By default, limiter uses Redis if `EKA_REDIS_URL` is set; otherwise it falls back to in-memory mode.
