from app import rate_limit


def test_rate_limit_allows_initial_requests() -> None:
    assert rate_limit.allow_request("u_test")


def test_rate_limit_blocks_after_limit(monkeypatch) -> None:
    monkeypatch.setattr(rate_limit.settings, "rate_limit_requests_per_minute", 2)
    rate_limit._BUCKETS.clear()
    assert rate_limit.allow_request("u_limit")
    assert rate_limit.allow_request("u_limit")
    assert not rate_limit.allow_request("u_limit")
