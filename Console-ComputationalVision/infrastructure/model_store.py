from __future__ import annotations

from pathlib import Path
from ultralytics import YOLO

from shared.paths import ensure_path_first, list_files_with_extensions


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
        files = list_files_with_extensions(self._models_dir, (".pt",))
        return [path.as_posix() for path in files]

    def ensure_present(self, path: str) -> list[str]:
        models = self.list_models()
        return ensure_path_first(models, path)

    def load_labels(self, model_path: str) -> list[str]:
        model = YOLO(model_path)
        return _normalise_label_names(getattr(model, "names", {}))
