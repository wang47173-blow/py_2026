from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .tool_registry import ToolRegistry


@dataclass
class JsonRpcError(Exception):
    code: int
    message: str


def _ok(req_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def _err(req_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


def _validate_request(req: dict[str, Any]) -> None:
    if req.get("jsonrpc") != "2.0":
        raise JsonRpcError(-32600, "invalid jsonrpc version")
    if "method" not in req:
        raise JsonRpcError(-32600, "missing method")


def _dispatch_one(req: dict[str, Any], registry: ToolRegistry) -> dict[str, Any]:
    req_id = req.get("id")
    try:
        _validate_request(req)
        method = req["method"]
        params = req.get("params") or {}

        if method == "initialize":
            return _ok(req_id, {"serverInfo": {"name": "mcp-starter-plus", "version": "0.1.0"}})
        if method == "tools/list":
            return _ok(req_id, {"tools": sorted(list(registry._tools.keys()))})
        if method == "tools/call":
            name = params.get("name")
            args = params.get("arguments") or {}
            if not name:
                return _err(req_id, -32602, "missing tool name")
            return _ok(req_id, registry.call(name, args))
        return _err(req_id, -32601, f"method not found: {method}")
    except JsonRpcError as exc:
        return _err(req_id, exc.code, exc.message)


def dispatch_jsonrpc(payload: dict[str, Any] | list[dict[str, Any]], registry: ToolRegistry) -> dict[str, Any] | list[dict[str, Any]]:
    """Dispatch JSON-RPC single or batch payload."""
    if isinstance(payload, list):
        return [_dispatch_one(req, registry) for req in payload]
    return _dispatch_one(payload, registry)
