import asyncio

import pytest

pytest.importorskip("sqlalchemy")

from app.mcp_rpc import handle_mcp_rpc


def test_mcp_initialize() -> None:
    out = asyncio.run(handle_mcp_rpc({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}))
    assert out["jsonrpc"] == "2.0"
    assert out["id"] == 1
    assert "serverInfo" in out["result"]


def test_mcp_tools_list() -> None:
    out = asyncio.run(handle_mcp_rpc({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}))
    assert out["id"] == 2
    assert "tools" in out["result"]
