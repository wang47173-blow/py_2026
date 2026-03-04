from __future__ import annotations

from app.repositories.audit_repo import insert_query_chunks, insert_query_log


async def log_query(*, query_id: str, tenant_id: str, user_id: str, question_hash: str, top_k: int, latency_ms: int) -> None:
    await insert_query_log(
        query_id=query_id,
        tenant_id=tenant_id,
        user_id=user_id,
        question_hash=question_hash,
        top_k=top_k,
        latency_ms=latency_ms,
    )


async def log_query_chunks(*, query_id: str, chunks: list[dict]) -> None:
    await insert_query_chunks(query_id=query_id, chunks=chunks)
