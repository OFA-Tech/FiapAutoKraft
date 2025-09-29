from __future__ import annotations

import importlib
from pathlib import Path
from typing import Callable, TYPE_CHECKING

from shared.paths import ensure_path_first, list_files_with_extensions


if TYPE_CHECKING:  # pragma: no cover - type checking only
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
    def __init__(self, models_dir: Path, model_loader: Callable[[str], object] | None = None) -> None:
        self._models_dir = models_dir
        self._model_loader: Callable[[str], object] = model_loader or self._load_model

    def list_models(self) -> list[str]:
        files = list_files_with_extensions(self._models_dir, (".pt",))
        return [path.as_posix() for path in files]

    def ensure_present(self, path: str) -> list[str]:
        models = self.list_models()
        return ensure_path_first(models, path)

    def load_labels(self, model_path: str) -> list[str]:
        model = self._model_loader(model_path)
        return _normalise_label_names(getattr(model, "names", {}))

    def _load_model(self, model_path: str):
        try:
            module = importlib.import_module("ultralytics")
            YOLO = getattr(module, "YOLO")
        except (ImportError, AttributeError) as exc:  # pragma: no cover - requires missing dependency
            raise RuntimeError(
                "Ultralytics YOLO and OpenCV are required to load detection models. "
                "Install them with `pip install ultralytics opencv-python` and ensure system "
                "OpenCV dependencies like libGL are available."
            ) from exc
        return YOLO(model_path)
