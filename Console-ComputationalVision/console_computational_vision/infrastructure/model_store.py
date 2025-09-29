from __future__ import annotations

from pathlib import Path
from ultralytics import YOLO


def _normalise_label_names(names) -> list[str]:
    if isinstance(names, dict):
        return [names[index] for index in sorted(names)]
    if isinstance(names, (list, tuple)):
        return list(names)
    try:
        return [value for _, value in sorted(names.items())]
    except AttributeError:
        return [str(names)]


class ModelStore:
    def __init__(self, models_dir: Path) -> None:
        self._models_dir = models_dir

    def list_models(self) -> list[str]:
        if not self._models_dir.exists():
            return []
        paths: list[str] = []
        for file_path in sorted(self._models_dir.rglob("*.pt")):
            paths.append(file_path.as_posix())
        return paths

    def ensure_present(self, path: str) -> list[str]:
        models = self.list_models()
        if path and path not in models:
            models = [path] + models
        return models

    def load_labels(self, model_path: str) -> list[str]:
        model = YOLO(model_path)
        return _normalise_label_names(getattr(model, "names", {}))
