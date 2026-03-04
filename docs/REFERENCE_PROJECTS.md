# Reference Projects (GitHub-style patterns)

This project improvement pass references patterns commonly used in high-quality open-source AI backends:

1. **modelcontextprotocol/python-sdk**
   - Why: canonical MCP protocol behavior (JSON-RPC request/response, tools/resources/prompts list).
   - Adopted here: added `/mcp` JSON-RPC endpoint with `initialize`, `tools/list`, `resources/list`, `prompts/list`, `tools/call` dispatch.

2. **langchain-ai/langserve**
   - Why: production-ish service layering around model/tool invocation.
   - Adopted here: structured tool dispatch in dedicated module (`app/mcp_rpc.py`) instead of endpoint-inline logic.

3. **open-webui/open-webui** (service-side hardening patterns)
   - Why: practical API ergonomics and compatibility-first endpoints.
   - Adopted here: kept existing REST endpoints for backward compatibility, while adding a protocol-oriented RPC endpoint.

> Note: exact upstream APIs evolve; this repo adopts the **design patterns** to improve architecture/readability/interoperability.
