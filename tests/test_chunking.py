from app.chunking import chunk_text, fake_embedding


def test_chunk_text_splits_with_overlap() -> None:
    text = "a" * 1200
    chunks = chunk_text(text, chunk_size=500, overlap=100)
    assert len(chunks) >= 3
    assert len(chunks[0]) == 500


def test_fake_embedding_shape() -> None:
    vec = fake_embedding("hello", dim=8)
    assert len(vec) == 8
    assert all(isinstance(v, float) for v in vec)
