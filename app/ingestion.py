from __future__ import annotations

import asyncio
import hashlib
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import text

from app.acl import build_acl_rules
from app.chunking import chunk_text
from app.config import settings
from app.db import engine
from app.rag import embed_texts

SUPPORTED_EXT = {".md", ".txt"}


def _resolve_data_source(data_source: str) -> Path:
    root = Path(settings.ingest_data_root).resolve()
    target = Path(data_source).resolve()
    if root not in [target, *target.parents]:
        raise ValueError(f"data_source must be under ingest_data_root: {root}")
    if not target.exists() or not target.is_dir():
        raise ValueError(f"data_source is not a directory: {target}")
    return target


async def init_schema() -> None:
    queries = [
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
        "ALTER TABLE ingest_jobs ADD COLUMN IF NOT EXISTS retry_count INT NOT NULL DEFAULT 0",
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
            metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """,
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

    async with engine.begin() as conn:
        for q in queries:
            await conn.execute(text(q))


async def create_index_job(
    *,
    data_source: str,
    tenant_id: UUID,
    visibility_policy: dict[str, Any],
    tags: list[str],
    idempotency_key: str | None,
) -> UUID:
    await init_schema()
    _resolve_data_source(data_source)

    async with engine.begin() as conn:
        if idempotency_key:
            existing = await conn.execute(
                text("SELECT id FROM ingest_jobs WHERE tenant_id=:tenant_id AND idempotency_key=:k"),
                {"tenant_id": str(tenant_id), "k": idempotency_key},
            )
            row = existing.first()
            if row:
                return row[0]

        job_id = uuid4()
        await conn.execute(
            text(
                """
                INSERT INTO ingest_jobs(id, tenant_id, data_source, visibility_policy, tags, status, idempotency_key)
                VALUES(:id, :tenant_id, :data_source, CAST(:visibility_policy AS JSONB), CAST(:tags AS JSONB), 'queued', :k)
                """
            ),
            {
                "id": str(job_id),
                "tenant_id": str(tenant_id),
                "data_source": data_source,
                "visibility_policy": __import__("json").dumps(visibility_policy),
                "tags": __import__("json").dumps(tags),
                "k": idempotency_key,
            },
        )
    return job_id


async def get_job_status(job_id: UUID) -> dict[str, Any] | None:
    await init_schema()
    async with engine.connect() as conn:
        result = await conn.execute(
            text(
                "SELECT id, status, processed_docs, processed_chunks, error_message "
                "FROM ingest_jobs WHERE id=:id"
            ),
            {"id": str(job_id)},
        )
        row = result.first()
        if not row:
            return None
        return {
            "job_id": row[0],
            "status": row[1],
            "processed_docs": row[2],
            "processed_chunks": row[3],
            "error_message": row[4],
        }


async def run_index_job(job_id: UUID) -> None:
    await asyncio.sleep(0)

    max_attempts = max(1, settings.ingest_max_retries + 1)
    for attempt in range(1, max_attempts + 1):
        docs = 0
        chunks = 0
        try:
            async with engine.begin() as conn:
                job_rs = await conn.execute(
                    text("SELECT data_source, tenant_id, visibility_policy, tags FROM ingest_jobs WHERE id=:id"),
                    {"id": str(job_id)},
                )
                job = job_rs.first()
                if not job:
                    return

                data_source, tenant_id, visibility_policy, tags = job
                await conn.execute(
                    text(
                        "UPDATE ingest_jobs SET status='running', retry_count=:r, updated_at=NOW() WHERE id=:id"
                    ),
                    {"id": str(job_id), "r": attempt - 1},
                )

            folder = _resolve_data_source(data_source)
            for p in sorted(folder.iterdir()):
                if p.suffix.lower() not in SUPPORTED_EXT or not p.is_file():
                    continue
                content = p.read_text(encoding="utf-8", errors="ignore")
                split = chunk_text(content)
                if not split:
                    continue
                docs += 1
                checksum = hashlib.sha256(content.encode("utf-8", errors="ignore")).hexdigest()
                doc_id = uuid4()

                async with engine.begin() as conn:
                    await conn.execute(
                        text(
                            """
                            INSERT INTO documents(id, tenant_id, source_uri, title, checksum, ingest_job_id)
                            VALUES(:id, :tenant_id, :source_uri, :title, :checksum, :ingest_job_id)
                            """
                        ),
                        {
                            "id": str(doc_id),
                            "tenant_id": str(tenant_id),
                            "source_uri": str(p),
                            "title": p.name,
                            "checksum": checksum,
                            "ingest_job_id": str(job_id),
                        },
                    )

                    embeddings = await embed_texts(split)
                    for i, c in enumerate(split):
                        chunk_id = uuid4()
                        chunks += 1
                        await conn.execute(
                            text(
                                """
                                INSERT INTO document_chunks(id, tenant_id, document_id, chunk_index, content, embedding, metadata)
                                VALUES(:id, :tenant_id, :document_id, :chunk_index, :content, CAST(:embedding AS JSONB), CAST(:metadata AS JSONB))
                                """
                            ),
                            {
                                "id": str(chunk_id),
                                "tenant_id": str(tenant_id),
                                "document_id": str(doc_id),
                                "chunk_index": i,
                                "content": c,
                                "embedding": __import__("json").dumps(embeddings[i]),
                                "metadata": __import__("json").dumps(
                                    {"visibility_policy": visibility_policy, "tags": tags}
                                ),
                            },
                        )

                        for rule in build_acl_rules(visibility_policy):
                            await conn.execute(
                                text(
                                    """
                                    INSERT INTO acl_policies(id, tenant_id, resource_type, resource_id, effect, subject_type, subject_id)
                                    VALUES(:id, :tenant_id, 'chunk', :resource_id, :effect, :subject_type, :subject_id)
                                    """
                                ),
                                {
                                    "id": str(uuid4()),
                                    "tenant_id": str(tenant_id),
                                    "resource_id": str(chunk_id),
                                    "effect": str(rule["effect"]),
                                    "subject_type": str(rule["subject_type"]),
                                    "subject_id": rule["subject_id"],
                                },
                            )

                async with engine.begin() as conn:
                    await conn.execute(
                        text(
                            "UPDATE ingest_jobs SET processed_docs=:d, processed_chunks=:c, updated_at=NOW() WHERE id=:id"
                        ),
                        {"d": docs, "c": chunks, "id": str(job_id)},
                    )

            async with engine.begin() as conn:
                await conn.execute(
                    text(
                        "UPDATE ingest_jobs SET status='succeeded', processed_docs=:d, processed_chunks=:c, updated_at=NOW() WHERE id=:id"
                    ),
                    {"d": docs, "c": chunks, "id": str(job_id)},
                )
            return
        except Exception as exc:
            if attempt >= max_attempts:
                async with engine.begin() as conn:
                    await conn.execute(
                        text(
                            "UPDATE ingest_jobs SET status='failed', error_message=:e, retry_count=:r, updated_at=NOW() WHERE id=:id"
                        ),
                        {"e": str(exc), "id": str(job_id), "r": attempt - 1},
                    )
                return
            await asyncio.sleep(min(2**attempt, 8))
