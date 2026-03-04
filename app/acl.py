from __future__ import annotations

from typing import Any


def build_acl_rules(visibility_policy: dict[str, Any]) -> list[dict[str, str | None]]:
    """Create ACL rows from visibility policy with deny-overrides semantics."""
    rules: list[dict[str, str | None]] = []
    allow_users = visibility_policy.get("allow_users", [])
    allow_groups = visibility_policy.get("allow_groups", [])
    deny_users = visibility_policy.get("deny_users", [])
    deny_groups = visibility_policy.get("deny_groups", [])

    if visibility_policy.get("scope") == "internal" or visibility_policy.get("allow_all") is True:
        rules.append({"effect": "allow", "subject_type": "all", "subject_id": None})

    for uid in allow_users:
        rules.append({"effect": "allow", "subject_type": "user", "subject_id": str(uid)})
    for gid in allow_groups:
        rules.append({"effect": "allow", "subject_type": "group", "subject_id": str(gid)})

    for uid in deny_users:
        rules.append({"effect": "deny", "subject_type": "user", "subject_id": str(uid)})
    for gid in deny_groups:
        rules.append({"effect": "deny", "subject_type": "group", "subject_id": str(gid)})

    return rules
