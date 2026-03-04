from __future__ import annotations

import asyncio
import hashlib
import time
from typing import Any
from uuid import uuid4

from langchain_fireworks import ChatFireworks, FireworksEmbeddings
from sqlalchemy import text

from app.audit import log_query, log_query_chunks
from app.config import settings
from app.db import engine
from app.guardrails import enforce_refusal_if_needed, validate_citations
from app.repositories.chunk_repo import retrieve_authorized_chunks

_EMBEDDINGS: FireworksEmbeddings | None = None
_LLM: ChatFireworks | None = None


def _require_fireworks_key() -> str:
    if not settings.fireworks_api_key:
        raise ValueError("Missing EKA_FIREWORKS_API_KEY in .env (leave placeholder in .env.example and fill locally).")
    return settings.fireworks_api_key


def _get_embeddings() -> FireworksEmbeddings:
    global _EMBEDDINGS
    if _EMBEDDINGS is None:
        _EMBEDDINGS = FireworksEmbeddings(model=settings.fireworks_model, fireworks_api_key=_require_fireworks_key())
    return _EMBEDDINGS


def _get_llm() -> ChatFireworks:
    global _LLM
    if _LLM is None:
        _LLM = ChatFireworks(model=settings.fireworks_model, fireworks_api_key=_require_fireworks_key(), temperature=0)
    return _LLM


async def embed_texts(texts: list[str]) -> list[list[float]]:
    emb = _get_embeddings()
    vectors = await asyncio.to_thread(emb.embed_documents, texts)
    dim = settings.embedding_dim
    return [(v[:dim] + [0.0] * max(0, dim - len(v)))[:dim] for v in vectors]


async def embed_query(query: str) -> list[float]:
    emb = _get_embeddings()
    v = await asyncio.to_thread(emb.embed_query, query)
    dim = settings.embedding_dim
    return (v[:dim] + [0.0] * max(0, dim - len(v)))[:dim]


async def retrieve_chunks(
    *, tenant_id: str, user_id: str, top_k: int, filters: dict[str, Any], query_embedding: list[float]
) -> list[dict[str, Any]]:
    tag_filter = (filters or {}).get("tag")
    return await retrieve_authorized_chunks(
        tenant_id=tenant_id,
        user_id=user_id,
        top_k=top_k,
        tag_filter=tag_filter,
        query_embedding=query_embedding,
    )


async def generate_answer(question: str, chunks: list[dict[str, Any]]) -> str:
    llm = _get_llm()
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
    answer = refusal if refusal else await generate_answer(question, chunks)

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
