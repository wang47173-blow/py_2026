from __future__ import annotations

from sqlalchemy import text

from app.config import settings
from app.db import engine


def vector_literal(values: list[float]) -> str:
    dim = settings.embedding_dim
    vec = values[:dim] + [0.0] * max(0, dim - len(values))
    return "[" + ",".join(f"{v:.8f}" for v in vec[:dim]) + "]"


async def retrieve_authorized_chunks(
    *, tenant_id: str, user_id: str, top_k: int, tag_filter: str | None, query_embedding: list[float]
) -> list[dict]:
    q_vec = vector_literal(query_embedding)
    sql = text(
        """
        WITH ug AS (
            SELECT group_id::text AS group_id
            FROM user_groups
            WHERE tenant_id=CAST(:tenant_id AS uuid) AND user_id=CAST(:user_id AS uuid)
        ),
        ranked AS (
            SELECT
                c.id AS chunk_id,
                c.document_id,
                c.content,
                d.source_uri,
                (c.embedding_vec <=> CAST(:q_vec AS vector)) AS distance,
                COALESCE(BOOL_OR(ap.effect='deny'), false) AS denied,
                COALESCE(BOOL_OR(ap.effect='allow'), false) AS allowed,
                COUNT(ap.id) AS rule_count
            FROM document_chunks c
            JOIN documents d ON d.id = c.document_id
            LEFT JOIN acl_policies ap
              ON ap.tenant_id = c.tenant_id
             AND ap.resource_type='chunk'
             AND ap.resource_id = c.id
             AND (
                ap.subject_type='all'
                OR (ap.subject_type='user' AND ap.subject_id::text=:user_id)
                OR (ap.subject_type='group' AND ap.subject_id::text IN (SELECT group_id FROM ug))
             )
            WHERE c.tenant_id=CAST(:tenant_id AS uuid)
              AND (:tag_filter IS NULL OR (c.metadata->'tags') ? :tag_filter)
            GROUP BY c.id, c.document_id, c.content, d.source_uri, c.embedding_vec
        )
        SELECT chunk_id, document_id, content, source_uri, distance
        FROM ranked
        WHERE denied = false AND (rule_count = 0 OR allowed = true)
        ORDER BY distance ASC
        LIMIT :top_k
        """
    )
    async with engine.connect() as conn:
        rs = await conn.execute(
            sql,
            {
                "tenant_id": tenant_id,
                "user_id": user_id,
                "tag_filter": tag_filter,
                "q_vec": q_vec,
                "top_k": max(1, min(top_k, settings.max_top_k)),
            },
        )
        rows = rs.fetchall()

    return [
        {
            "chunk_id": r[0],
            "document_id": r[1],
            "content": r[2],
            "snippet": (r[2] or "")[:240],
            "source": r[3],
            "score": 1.0 - float(r[4]),
        }
        for r in rows
    ]
