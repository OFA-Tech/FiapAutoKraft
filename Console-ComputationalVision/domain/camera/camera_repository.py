from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable, Protocol

from .camera import Camera, Frame, Resolution


class CameraStream(Protocol):
    def read(self) -> Frame | None:
        """Return the latest frame from the stream or ``None`` if unavailable."""

    def close(self) -> None:
        """Release the underlying camera resources."""


class CameraRepository(ABC):
    """Abstract camera repository able to enumerate and open cameras."""

    @abstractmethod
    def list_cameras(self) -> Iterable[Camera]:
        raise NotImplementedError

    @abstractmethod
    def open(self, index: int, resolution: Resolution, target_fps: float) -> CameraStream:
        raise NotImplementedError
