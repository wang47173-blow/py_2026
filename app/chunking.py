from __future__ import annotations


def chunk_text(text: str, *, chunk_size: int = 700, overlap: int = 100) -> list[str]:
    """Simple deterministic character-based chunker for M1."""
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


def fake_embedding(text: str, dim: int = 8) -> list[float]:
    """M1 placeholder embedding to keep ingestion locally runnable without external model calls."""
    seed = sum(ord(c) for c in text)
    return [((seed + i * 31) % 1000) / 1000.0 for i in range(dim)]
