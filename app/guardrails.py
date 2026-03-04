from __future__ import annotations

import re

_INJECTION_REGEX = [
    re.compile(r"\bignore\s+(all\s+)?(previous|prior|system)\s+instructions\b", re.IGNORECASE),
    re.compile(r"\breveal\s+(api\s+)?key\b", re.IGNORECASE),
    re.compile(r"\bdump\s+secrets?\b", re.IGNORECASE),
    re.compile(r"忽略(所有)?(之前|系统)?指令"),
    re.compile(r"泄露(所有)?密钥"),
    re.compile(r"base64|rot13|编码绕过", re.IGNORECASE),
]


def detect_prompt_injection(text: str) -> bool:
    return any(p.search(text or "") for p in _INJECTION_REGEX)


def enforce_refusal_if_needed(question: str, chunks: list[dict]) -> str | None:
    if detect_prompt_injection(question):
        return "我不能执行越权或泄露敏感信息的请求。"
    joined = "\n".join((c.get("content", "") or "") for c in chunks)
    if detect_prompt_injection(joined):
        return "检索到的文档包含可疑指令注入内容，我将忽略该指令并仅基于安全证据回答。"
    return None


def validate_citations(citations: list[dict]) -> bool:
    for c in citations:
        if not c.get("chunk_id") or not c.get("source") or not c.get("snippet"):
            return False
    return True
