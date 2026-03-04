"""initial schema

Revision ID: 20260304_01
Revises:
Create Date: 2026-03-04
"""

from __future__ import annotations

from alembic import op

revision = "20260304_01"
down_revision = None
branch_labels = None
depends_on = None


DDL = [
    "CREATE EXTENSION IF NOT EXISTS vector",
    """
    CREATE TABLE IF NOT EXISTS ingest_jobs (
        id UUID PRIMARY KEY,
        tenant_id UUID NOT NULL,
        data_source TEXT NOT NULL,
        visibility_policy JSONB NOT NULL DEFAULT '{}'::jsonb,
        tags JSONB NOT NULL DEFAULT '[]'::jsonb,
        status TEXT NOT NULL,
        processed_docs INT NOT NULL DEFAULT 0,
        processed_chunks INT NOT NULL DEFAULT 0,
        retry_count INT NOT NULL DEFAULT 0,
        idempotency_key TEXT,
        error_message TEXT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_ingest_jobs_tenant_idempo ON ingest_jobs(tenant_id, idempotency_key) WHERE idempotency_key IS NOT NULL",
    """
    CREATE TABLE IF NOT EXISTS documents (
        id UUID PRIMARY KEY,
        tenant_id UUID NOT NULL,
        source_uri TEXT NOT NULL,
        title TEXT NOT NULL,
        checksum TEXT NOT NULL,
        ingest_job_id UUID REFERENCES ingest_jobs(id),
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS document_chunks (
        id UUID PRIMARY KEY,
        tenant_id UUID NOT NULL,
        document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
        chunk_index INT NOT NULL,
        content TEXT NOT NULL,
        embedding JSONB NOT NULL,
        embedding_vec VECTOR(1024),
        metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_document_chunks_embedding_hnsw ON document_chunks USING hnsw (embedding_vec vector_l2_ops)",
    """
    CREATE TABLE IF NOT EXISTS users (
        id UUID PRIMARY KEY,
        tenant_id UUID NOT NULL,
        email TEXT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS groups (
        id UUID PRIMARY KEY,
        tenant_id UUID NOT NULL,
        name TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS user_groups (
        tenant_id UUID NOT NULL,
        user_id UUID NOT NULL,
        group_id UUID NOT NULL,
        PRIMARY KEY (tenant_id, user_id, group_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS acl_policies (
        id UUID PRIMARY KEY,
        tenant_id UUID NOT NULL,
        resource_type TEXT NOT NULL,
        resource_id UUID NOT NULL,
        effect TEXT NOT NULL,
        subject_type TEXT NOT NULL,
        subject_id UUID,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS query_logs (
        id UUID PRIMARY KEY,
        tenant_id UUID NOT NULL,
        user_id UUID NOT NULL,
        question_hash TEXT NOT NULL,
        top_k INT NOT NULL,
        latency_ms INT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS query_chunk_access (
        query_id UUID NOT NULL,
        chunk_id UUID NOT NULL,
        document_id UUID NOT NULL,
        rank INT NOT NULL,
        score DOUBLE PRECISION NOT NULL,
        PRIMARY KEY (query_id, chunk_id)
    )
    """,
]


def upgrade() -> None:
    for stmt in DDL:
        op.execute(stmt)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS query_chunk_access")
    op.execute("DROP TABLE IF EXISTS query_logs")
    op.execute("DROP TABLE IF EXISTS acl_policies")
    op.execute("DROP TABLE IF EXISTS user_groups")
    op.execute("DROP TABLE IF EXISTS groups")
    op.execute("DROP TABLE IF EXISTS users")
    op.execute("DROP TABLE IF EXISTS document_chunks")
    op.execute("DROP TABLE IF EXISTS documents")
    op.execute("DROP TABLE IF EXISTS ingest_jobs")
