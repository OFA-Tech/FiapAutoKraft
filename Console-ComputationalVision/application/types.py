from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from domain.motion.position import Position
from domain.vision.model import BoundingBox


@dataclass(frozen=True)
class CameraViewModel:
    label: str
    index: int
    resolution: tuple[int, int]
    backend: str | None = None


@dataclass(frozen=True)
class DetectionViewModel:
    boxes: Sequence[BoundingBox]
    fps: float
    inference_ms: float


@dataclass(frozen=True)
class PositionViewModel:
    position: Position


@dataclass(frozen=True)
class CommandStatusViewModel:
    status: str
    inflight: bool
