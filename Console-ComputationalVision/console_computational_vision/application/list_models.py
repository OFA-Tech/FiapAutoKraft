from __future__ import annotations

from ..infrastructure.model_store import ModelStore


class ListModelsUseCase:
    def __init__(self, store: ModelStore) -> None:
        self._store = store

    def execute(self, ensure: str | None = None) -> list[str]:
        models = self._store.list_models()
        if ensure:
            models = self._store.ensure_present(ensure)
        return models


class LoadModelLabelsUseCase:
    def __init__(self, store: ModelStore) -> None:
        self._store = store

    def execute(self, model_path: str) -> list[str]:
        return self._store.load_labels(model_path)
