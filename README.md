# Enterprise Knowledge Assistant Gateway (M1+)

This project now includes:
- MCP-compatible tool descriptors (`/mcp/tools`)
- `index_docs` ingestion (md/txt folder -> chunks -> embeddings -> DB)
- `rag_query` using **LangChain Fireworks GLM-5**
- `list_corpora` and resources endpoints
- health/readiness/metrics endpoints

## 1) Prepare `.env`

```bash
cp .env.example .env
```

Open `.env` and fill your key:

```env
EKA_FIREWORKS_API_KEY=
```

> Keep it empty in git, fill locally only.

## 2) Run with Docker

```bash
docker compose up --build
```

## 3) Quick API checks

```bash
curl http://localhost:8080/healthz
curl http://localhost:8080/readyz
curl http://localhost:8080/mcp/tools
```

## 4) Index sample docs

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

Get job status:

```bash
curl http://localhost:8080/mcp/tools/index_docs/<job_id>
```

## 5) Run `rag_query` (Fireworks GLM-5)

```bash
curl -X POST http://localhost:8080/mcp/tools/rag_query \
  -H 'Content-Type: application/json' \
  -d '{
    "question": "What does the handbook say about security?",
    "tenant_id": "11111111-1111-1111-1111-111111111111",
    "user_id": "22222222-2222-2222-2222-222222222222",
    "top_k": 3,
    "filters": {}
  }'
```

## Conda local run (`s_env`)

```bash
conda activate s_env
pip install -r requirements.txt pytest
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

## Tests

```bash
pytest -q
```
