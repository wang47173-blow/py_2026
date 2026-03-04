"""MCP metadata contracts."""

TOOLS = [
    {
        "name": "index_docs",
        "description": "Queue document indexing job. POST /mcp/tools/index_docs",
        "input": ["data_source", "tenant_id", "visibility_policy", "tags", "idempotency_key"],
    },
    {
        "name": "rag_query",
        "description": "Query enterprise KB via Fireworks GLM-5. POST /mcp/tools/rag_query",
        "input": ["question", "tenant_id", "user_id", "top_k", "filters"],
    },
    {
        "name": "list_corpora",
        "description": "List indexed docs and stats. GET /mcp/tools/list_corpora/{tenant_id}",
        "input": ["tenant_id"],
    },
]

RESOURCES = [
    {"uri": "/tenants/{id}/docs", "description": "Tenant document listing."},
    {"uri": "/tenants/{id}/stats", "description": "Tenant retrieval statistics."},
]

PROMPTS = [
    {
        "name": "enterprise_qa",
        "description": "Only answer using retrieved enterprise evidence; cite sources and refuse if evidence is insufficient.",
    }
]
