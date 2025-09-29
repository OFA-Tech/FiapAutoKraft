"""Application service layer orchestrating domain and data components."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from domain.entities import Detection
from data.repositories import DetectionProvider, DetectionResultRepository


@dataclass(frozen=True)
class VisionInferenceRequest:
    """Request DTO for running inference."""

    selected_labels: Sequence[str] | None = None
    limit: int | None = None


@dataclass(frozen=True)
class VisionInferenceResponse:
    """Response DTO produced by :class:`VisionInferenceUseCase`."""

    detections: Sequence[Detection]
    total: int


class VisionInferenceUseCase:
    """Coordinate detection providers and repositories to execute inference."""

    def __init__(
        self,
        detection_provider: DetectionProvider,
        detection_repository: DetectionResultRepository,
        logger,
    ) -> None:
        self._detection_provider = detection_provider
        self._detection_repository = detection_repository
        self._logger = logger

    def execute(self, request: VisionInferenceRequest) -> VisionInferenceResponse:
        batch = self._detection_provider.run_inference(
            selected_labels=request.selected_labels,
        )
        self._logger.info(
            "inference.completed total=%s labels=%s",
            len(batch.detections),
            [d.label for d in batch.detections],
        )
        self._detection_repository.store(batch)
        detections = batch.detections
        if request.limit is not None:
            detections = detections[: request.limit]
        return VisionInferenceResponse(detections=detections, total=len(batch.detections))


__all__ = [
    "VisionInferenceRequest",
    "VisionInferenceResponse",
    "VisionInferenceUseCase",
]
