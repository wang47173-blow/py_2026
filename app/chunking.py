from __future__ import annotations


def chunk_text(text: str, *, chunk_size: int = 700, overlap: int = 100) -> list[str]:
    """Simple deterministic character-based chunker."""
    cleaned = " ".join(text.split())
    if not cleaned:
        return []

    chunks: list[str] = []
    start = 0
    while start < len(cleaned):
        end = min(len(cleaned), start + chunk_size)
        chunks.append(cleaned[start:end])
        if end == len(cleaned):
            break
        start = max(0, end - overlap)
    return chunks
