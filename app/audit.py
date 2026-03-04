from __future__ import annotations

from sqlalchemy import text

from app.db import engine


async def log_query(*, query_id: str, tenant_id: str, user_id: str, question_hash: str, top_k: int, latency_ms: int) -> None:
    async with engine.begin() as conn:
        await conn.execute(
            text(
                """
                INSERT INTO query_logs(id, tenant_id, user_id, question_hash, top_k, latency_ms)
                VALUES(:id, :tenant_id, :user_id, :question_hash, :top_k, :latency_ms)
                """
            ),
            {
                "id": query_id,
                "tenant_id": tenant_id,
                "user_id": user_id,
                "question_hash": question_hash,
                "top_k": top_k,
                "latency_ms": latency_ms,
            },
        )


async def log_query_chunks(*, query_id: str, chunks: list[dict]) -> None:
    async with engine.begin() as conn:
        for rank, c in enumerate(chunks, start=1):
            await conn.execute(
                text(
                    """
                    INSERT INTO query_chunk_access(query_id, chunk_id, document_id, rank, score)
                    VALUES(:query_id, :chunk_id, :document_id, :rank, :score)
                    """
                ),
                {
                    "query_id": query_id,
                    "chunk_id": str(c.get("chunk_id")),
                    "document_id": str(c.get("document_id")),
                    "rank": rank,
                    "score": float(c.get("score", 0.0)),
                },
            )
