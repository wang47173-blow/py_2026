from __future__ import annotations

import hashlib
import json
import math
import time
from typing import Any
from uuid import uuid4

from langchain_fireworks import ChatFireworks, FireworksEmbeddings
from sqlalchemy import text

from app.audit import log_query, log_query_chunks
from app.authz import is_chunk_allowed
from app.config import settings
from app.db import engine
from app.guardrails import enforce_refusal_if_needed, validate_citations


def _require_fireworks_key() -> str:
    if not settings.fireworks_api_key:
        raise ValueError("Missing EKA_FIREWORKS_API_KEY in .env (leave placeholder in .env.example and fill locally).")
    return settings.fireworks_api_key


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


async def embed_texts(texts: list[str]) -> list[list[float]]:
    key = _require_fireworks_key()
    emb = FireworksEmbeddings(model=settings.fireworks_model, fireworks_api_key=key)
    return await __import__("asyncio").to_thread(emb.embed_documents, texts)


async def embed_query(query: str) -> list[float]:
    key = _require_fireworks_key()
    emb = FireworksEmbeddings(model=settings.fireworks_model, fireworks_api_key=key)
    return await __import__("asyncio").to_thread(emb.embed_query, query)


async def retrieve_chunks(
    *, tenant_id: str, user_id: str, top_k: int, filters: dict[str, Any], query_embedding: list[float]
) -> list[dict[str, Any]]:
    tag_filter = (filters or {}).get("tag")
    async with engine.connect() as conn:
        rs = await conn.execute(
            text(
                """
                SELECT c.id, c.document_id, c.content, c.embedding, c.metadata, d.source_uri
                FROM document_chunks c
                JOIN documents d ON d.id = c.document_id
                WHERE c.tenant_id = :tenant_id
                """
            ),
            {"tenant_id": tenant_id},
        )
        rows = rs.fetchall()

    scored: list[dict[str, Any]] = []
    for row in rows:
        metadata = row[4] if isinstance(row[4], dict) else json.loads(row[4] or "{}")
        tags = metadata.get("tags", [])
        if tag_filter and tag_filter not in tags:
            continue

        allowed = await is_chunk_allowed(tenant_id, user_id, str(row[0]))
        if not allowed:
            continue

        embedding = row[3] if isinstance(row[3], list) else json.loads(row[3])
        score = _cosine(query_embedding, [float(v) for v in embedding])
        scored.append(
            {
                "chunk_id": row[0],
                "document_id": row[1],
                "snippet": row[2][:240],
                "content": row[2],
                "source": row[5],
                "score": score,
            }
        )

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:max(1, min(top_k, settings.max_top_k))]


async def generate_answer(question: str, chunks: list[dict[str, Any]]) -> str:
    key = _require_fireworks_key()
    llm = ChatFireworks(model=settings.fireworks_model, fireworks_api_key=key, temperature=0)

    citations_text = "\n".join(
        f"[{i+1}] chunk_id={c['chunk_id']} source={c['source']}\n{c['content']}" for i, c in enumerate(chunks)
    )
    citations_text = citations_text[: settings.max_context_chars]

    prompt = (
        "你是企业知识助手。严格执行：1) 只基于证据回答；2) 必须给出证据编号；3) 证据不足就明确拒答。\n\n"
        f"问题: {question}\n\n证据:\n{citations_text}"
    )
    resp = await llm.ainvoke(prompt)
    return resp.content if hasattr(resp, "content") else str(resp)


async def rag_query(*, question: str, tenant_id: str, user_id: str, top_k: int, filters: dict[str, Any]) -> dict[str, Any]:
    start = time.perf_counter()

    q_emb = await embed_query(question)
    chunks = await retrieve_chunks(
        tenant_id=tenant_id,
        user_id=user_id,
        top_k=top_k,
        filters=filters,
        query_embedding=q_emb,
    )

    refusal = enforce_refusal_if_needed(question, chunks)
    if refusal:
        answer = refusal
    else:
        answer = await generate_answer(question, chunks)

    latency = int((time.perf_counter() - start) * 1000)
    citations = [{"chunk_id": c["chunk_id"], "source": c["source"], "snippet": c["snippet"]} for c in chunks]
    if not validate_citations(citations):
        answer = "系统检测到引用格式异常，拒绝返回不可信结果。"
        citations = []

    query_id = str(uuid4())
    await log_query(
        query_id=query_id,
        tenant_id=tenant_id,
        user_id=user_id,
        question_hash=hashlib.sha256(question.encode("utf-8")).hexdigest(),
        top_k=top_k,
        latency_ms=latency,
    )
    await log_query_chunks(query_id=query_id, chunks=chunks)

    return {"answer": answer, "citations": citations, "used_chunks": len(chunks), "latency_ms": latency}


async def list_corpora(tenant_id: str) -> dict[str, Any]:
    async with engine.connect() as conn:
        docs_rs = await conn.execute(
            text(
                "SELECT id, title, source_uri, created_at FROM documents WHERE tenant_id=:tenant_id ORDER BY created_at DESC"
            ),
            {"tenant_id": tenant_id},
        )
        docs = [
            {"id": r[0], "title": r[1], "source_uri": r[2], "created_at": str(r[3])}
            for r in docs_rs.fetchall()
        ]
        stats_rs = await conn.execute(
            text(
                "SELECT COUNT(*) AS doc_count, COALESCE((SELECT COUNT(*) FROM document_chunks c WHERE c.tenant_id=:tenant_id),0) AS chunk_count "
                "FROM documents d WHERE d.tenant_id=:tenant_id"
            ),
            {"tenant_id": tenant_id},
        )
        s = stats_rs.first()

    return {"docs": docs, "stats": {"doc_count": int(s[0]), "chunk_count": int(s[1])}}
