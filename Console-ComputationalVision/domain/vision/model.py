from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence


@dataclass(frozen=True)
class Model:
    path: str
    labels: Sequence[str]


@dataclass(frozen=True)
class BoundingBox:
    label: str
    confidence: float
    xyxy: tuple[int, int, int, int]
    center: tuple[int, int]


@dataclass(frozen=True)
class InferenceResult:
    boxes: Sequence[BoundingBox]
    annotated_frame: "np.ndarray"
    duration_ms: float
    fps: float

    def labels(self) -> Iterable[str]:
        for box in self.boxes:
            yield box.label


try:
    import numpy as np  # type: ignore
except Exception:  # pragma: no cover
    np = None  # type: ignore
