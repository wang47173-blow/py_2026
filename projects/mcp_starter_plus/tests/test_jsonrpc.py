from mcp_starter_plus.jsonrpc import dispatch_jsonrpc
from mcp_starter_plus.tool_registry import ToolRegistry, ToolSpec


def test_initialize() -> None:
    reg = ToolRegistry()
    out = dispatch_jsonrpc({"jsonrpc": "2.0", "id": 1, "method": "initialize"}, reg)
    assert out["result"]["serverInfo"]["name"] == "mcp-starter-plus"


def test_batch_and_validation() -> None:
    reg = ToolRegistry()
    out = dispatch_jsonrpc([
        {"jsonrpc": "2.0", "id": 1, "method": "initialize"},
        {"id": 2, "method": "initialize"},
    ], reg)
    assert len(out) == 2
    assert "result" in out[0]
    assert out[1]["error"]["code"] == -32600


def test_tool_call_with_schema_and_idempotency() -> None:
    reg = ToolRegistry()
    reg.register(ToolSpec(name="sum", required_fields={"a", "b"}, handler=lambda x: {"value": x["a"] + x["b"]}))

    req = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {"name": "sum", "arguments": {"a": 1, "b": 2, "idempotency_key": "k1"}},
    }
    first = dispatch_jsonrpc(req, reg)
    second = dispatch_jsonrpc(req, reg)
    assert first["result"]["value"] == 3
    assert second["result"]["cached"] is True
