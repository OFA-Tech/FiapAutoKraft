"""Domain entities and value objects for the vision pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class BoundingBox:
    """Axis-aligned bounding box in pixel coordinates."""

    x1: int
    y1: int
    x2: int
    y2: int

    def as_tuple(self) -> tuple[int, int, int, int]:
        """Return the bounding box as a tuple."""

        return self.x1, self.y1, self.x2, self.y2


@dataclass(frozen=True)
class Detection:
    """Represents a single detected object on a frame."""

    label: str
    confidence: float
    bounding_box: BoundingBox
    center: tuple[int, int]


@dataclass(frozen=True)
class DetectionBatch:
    """Container holding a sequence of detections with metadata."""

    detections: Sequence[Detection]
    frame_timestamp: float


__all__ = ["BoundingBox", "Detection", "DetectionBatch"]
