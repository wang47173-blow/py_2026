"""initial schema

Revision ID: 20260304_01
Revises:
Create Date: 2026-03-04
"""

from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260304_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute(
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
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS ingest_jobs")
