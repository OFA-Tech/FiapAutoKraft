import types
from pathlib import Path

import pytest

from infrastructure.model_store import ModelStore


def test_load_labels_uses_injected_loader(tmp_path: Path) -> None:
    loader_calls: list[str] = []

    def fake_loader(path: str) -> object:
        loader_calls.append(path)
        return types.SimpleNamespace(names={0: "widget", 1: "gadget"})

    store = ModelStore(tmp_path, model_loader=fake_loader)

    labels = store.load_labels("/models/example.pt")

    assert loader_calls == ["/models/example.pt"]
    assert labels == ["widget", "gadget"]


def test_load_labels_missing_dependencies(monkeypatch, tmp_path: Path) -> None:
    store = ModelStore(tmp_path)

    def fake_import(_module: str):
        raise ImportError("boom")

    monkeypatch.setattr("infrastructure.model_store.importlib.import_module", fake_import)

    with pytest.raises(RuntimeError) as excinfo:
        store.load_labels("/models/example.pt")

    assert "Ultralytics YOLO" in str(excinfo.value)

