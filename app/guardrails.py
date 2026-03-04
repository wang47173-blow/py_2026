from __future__ import annotations

INJECTION_PATTERNS = [
    "ignore previous instructions",
    "忽略系统指令",
    "泄露密钥",
    "reveal api key",
    "dump secrets",
]


def detect_prompt_injection(text: str) -> bool:
    lowered = text.lower()
    return any(p in lowered for p in INJECTION_PATTERNS)


def enforce_refusal_if_needed(question: str, chunks: list[dict]) -> str | None:
    if detect_prompt_injection(question):
        return "我不能执行越权或泄露敏感信息的请求。"
    joined = "\n".join((c.get("content", "") or "") for c in chunks).lower()
    if detect_prompt_injection(joined):
        return "检索到的文档包含可疑指令注入内容，我将忽略该指令并仅基于安全证据回答。"
    return None


def validate_citations(citations: list[dict]) -> bool:
    for c in citations:
        if not c.get("chunk_id") or not c.get("source") or not c.get("snippet"):
            return False
    return True
