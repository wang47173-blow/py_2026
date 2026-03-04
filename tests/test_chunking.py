from app.chunking import chunk_text


def test_chunk_text_splits_with_overlap() -> None:
    text = "a" * 1200
    chunks = chunk_text(text, chunk_size=500, overlap=100)
    assert len(chunks) >= 3
    assert len(chunks[0]) == 500


def test_chunk_text_empty_input() -> None:
    assert chunk_text("   \n\t ") == []
