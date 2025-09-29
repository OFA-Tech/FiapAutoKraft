from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .camera.camera import Frame
from .motion.position import Position
from .vision.model import BoundingBox


@dataclass(frozen=True)
class PositionUpdated:
    position: Position


@dataclass(frozen=True)
class DetectionProduced:
    frame: Frame
    boxes: Sequence[BoundingBox]
    fps: float
    inference_ms: float


@dataclass(frozen=True)
class DeviceStateChanged:
    description: str


@dataclass(frozen=True)
class ErrorRaised:
    message: str
    exception: Exception | None = None
