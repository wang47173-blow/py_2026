"""MCP skeleton and M1 tool contracts."""

TOOLS = [
    {
        "name": "index_docs",
        "description": "Queue document indexing job. POST /mcp/tools/index_docs",
        "input": ["data_source", "tenant_id", "visibility_policy", "tags", "idempotency_key"],
    },
    {
        "name": "rag_query",
        "description": "(M2+) Query enterprise knowledge base with ACL and citations.",
    },
    {
        "name": "list_corpora",
        "description": "(M2+) List corpora and stats for tenant.",
    },
]

RESOURCES = [
    {"uri": "/tenants/{id}/docs", "description": "Tenant document listing. (M2+)"},
    {"uri": "/tenants/{id}/stats", "description": "Tenant retrieval statistics. (M2+)"},
]

PROMPTS = [
    {
        "name": "enterprise_qa",
        "description": "Enterprise QA prompt with citation-first and refusal rules.",
    }
]
