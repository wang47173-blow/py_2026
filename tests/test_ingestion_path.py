from pathlib import Path

import pytest

from app import ingestion


def test_resolve_data_source_rejects_outside_root(monkeypatch, tmp_path: Path) -> None:
    root = tmp_path / "data"
    root.mkdir()
    outside = tmp_path / "other"
    outside.mkdir()

    monkeypatch.setattr(ingestion.settings, "ingest_data_root", str(root))

    with pytest.raises(ValueError):
        ingestion._resolve_data_source(str(outside))
