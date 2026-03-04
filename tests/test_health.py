from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_healthz_ok() -> None:
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_mcp_skeleton_endpoints() -> None:
    assert client.get("/mcp/tools").status_code == 200
    assert client.get("/mcp/resources").status_code == 200
    assert client.get("/mcp/prompts").status_code == 200
