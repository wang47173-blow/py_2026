from __future__ import annotations

from sqlalchemy import text

from app.db import engine


async def get_user_group_ids(tenant_id: str, user_id: str) -> set[str]:
    async with engine.connect() as conn:
        rs = await conn.execute(
            text("SELECT group_id FROM user_groups WHERE tenant_id=:tenant_id AND user_id=:user_id"),
            {"tenant_id": tenant_id, "user_id": user_id},
        )
        return {str(r[0]) for r in rs.fetchall()}


async def is_chunk_allowed(tenant_id: str, user_id: str, chunk_id: str) -> bool:
    groups = await get_user_group_ids(tenant_id, user_id)
    async with engine.connect() as conn:
        rs = await conn.execute(
            text(
                """
                SELECT effect, subject_type, subject_id
                FROM acl_policies
                WHERE tenant_id=:tenant_id AND resource_type='chunk' AND resource_id=:chunk_id
                """
            ),
            {"tenant_id": tenant_id, "chunk_id": chunk_id},
        )
        rules = rs.fetchall()

    if not rules:
        return True  # default allow inside tenant for M2 baseline

    denied = False
    allowed = False
    for effect, subject_type, subject_id in rules:
        sid = str(subject_id) if subject_id else None
        matched = (
            subject_type == "all"
            or (subject_type == "user" and sid == user_id)
            or (subject_type == "group" and sid in groups)
        )
        if not matched:
            continue
        if effect == "deny":
            denied = True
        if effect == "allow":
            allowed = True

    if denied:
        return False
    return allowed
