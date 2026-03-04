# mcp-starter-plus

`mcp-starter-plus` 是一个**新建的独立子项目**：
- 参考了高质量 GitHub MCP 服务项目的常见架构思路（协议层、工具注册层、执行层分离）
- 在“修改版”里修复了常见小缺陷，并加入创新点

## 参考来源（思路层）
- modelcontextprotocol/python-sdk（协议建模）
- langserve / 现代 API 框架（分层与可测试性）

> 本项目不是复制源码，而是基于通用工程实践自行实现。

## 修复的小缺陷（相对常见 demo）
1. **严格 JSON-RPC 校验**：请求缺少 `jsonrpc/method/id` 时返回标准错误码。
2. **Batch 请求支持**：支持 JSON-RPC 批量请求，逐条返回结果。
3. **工具参数校验**：工具调用统一经过 schema 验证，避免隐式 KeyError。
4. **幂等缓存（可选）**：对带 `idempotency_key` 的调用做短时缓存。

## 创新点
- **自适应降级响应**：工具失败时可配置返回“结构化 fallback”，便于前端/Agent 继续处理。
- **内置可观测事件钩子**：每个请求触发 `before_call/after_call/on_error` 事件，方便接 tracing/metrics。

## 快速运行测试

```bash
pytest -q projects/mcp_starter_plus/tests
```
