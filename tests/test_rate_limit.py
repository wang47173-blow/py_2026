from app.rate_limit import allow_request


def test_rate_limit_allows_initial_requests() -> None:
    assert allow_request("u_test")
