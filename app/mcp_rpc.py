from __future__ import annotations

from typing import Any
from uuid import UUID

from app.ingestion import create_index_job
from app.mcp_skeleton import PROMPTS, RESOURCES, TOOLS
from app.rag import list_corpora, rag_query


async def handle_mcp_rpc(body: dict[str, Any]) -> dict[str, Any]:
    """Minimal MCP-style JSON-RPC dispatcher."""

    req_id = body.get("id")
    method = body.get("method")
    params = body.get("params") or {}

    if method == "initialize":
        return _ok(req_id, {"serverInfo": {"name": "eka-gateway", "version": "0.1.0"}})

    if method == "tools/list":
        return _ok(req_id, {"tools": TOOLS})

    if method == "resources/list":
        return _ok(req_id, {"resources": RESOURCES})

    if method == "prompts/list":
        return _ok(req_id, {"prompts": PROMPTS})

    if method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments") or {}
        try:
            result = await _call_tool(tool_name, arguments)
            return _ok(req_id, {"content": [{"type": "json", "json": result}]})
        except Exception as exc:  # noqa: BLE001
            return _err(req_id, -32000, str(exc))

    return _err(req_id, -32601, f"Method not found: {method}")


async def _call_tool(name: str | None, args: dict[str, Any]) -> dict[str, Any]:
    if name == "index_docs":
        job_id = await create_index_job(
            data_source=str(args["data_source"]),
            tenant_id=UUID(str(args["tenant_id"])),
            visibility_policy=dict(args.get("visibility_policy", {})),
            tags=list(args.get("tags", [])),
            idempotency_key=args.get("idempotency_key"),
        )
        return {"job_id": str(job_id)}

    if name == "rag_query":
        return await rag_query(
            question=str(args["question"]),
            tenant_id=str(args["tenant_id"]),
            user_id=str(args["user_id"]),
            top_k=int(args.get("top_k", 5)),
            filters=dict(args.get("filters", {})),
        )

    if name == "list_corpora":
        return await list_corpora(str(args["tenant_id"]))

    raise ValueError(f"Unsupported tool: {name}")


def _ok(req_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def _err(req_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}
