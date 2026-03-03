"""MCP skeleton for M0.

This module provides placeholder structures for tools/resources/prompts so the
interface shape is visible early and can be expanded in M1+.
"""

TOOLS = [
    {"name": "index_docs", "description": "Queue document indexing job."},
    {"name": "rag_query", "description": "Query enterprise knowledge base."},
    {"name": "list_corpora", "description": "List corpora and stats for tenant."},
]

RESOURCES = [
    {"uri": "/tenants/{id}/docs", "description": "Tenant document listing."},
    {"uri": "/tenants/{id}/stats", "description": "Tenant retrieval statistics."},
]

PROMPTS = [
    {
        "name": "enterprise_qa",
        "description": "Enterprise QA prompt with citation-first and refusal rules.",
    }
]
