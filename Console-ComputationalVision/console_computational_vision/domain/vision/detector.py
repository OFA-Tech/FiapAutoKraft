from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable, Protocol, Sequence

from .model import InferenceResult
from ..camera.camera import Frame


class Detector(ABC):
    """Performs inference on frames captured from a camera."""

    @abstractmethod
    def labels(self) -> Sequence[str]:
        raise NotImplementedError


class DetectorFactory(Protocol):
    def create(
        self,
        model_path: str,
        device: str | None = None,
    ) -> Detector:
        ...

    @abstractmethod
    def infer(
        self,
        frame: Frame,
        selected_labels: Iterable[str] | None = None,
        confidence_threshold: float = 0.5,
    ) -> InferenceResult:
        raise NotImplementedError
