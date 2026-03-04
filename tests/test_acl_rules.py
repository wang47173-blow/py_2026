from app.acl import build_acl_rules


def test_build_acl_rules_internal_allow_all() -> None:
    rules = build_acl_rules({"scope": "internal"})
    assert any(r["effect"] == "allow" and r["subject_type"] == "all" for r in rules)


def test_build_acl_rules_with_deny() -> None:
    rules = build_acl_rules({"allow_users": ["u1"], "deny_users": ["u1"]})
    assert any(r["effect"] == "allow" for r in rules)
    assert any(r["effect"] == "deny" for r in rules)
