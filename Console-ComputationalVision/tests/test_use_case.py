"""Unit tests for the vision inference use case."""

from __future__ import annotations

import logging

from data.repositories import InMemoryDetectionProvider, InMemoryDetectionRepository
from domain.entities import BoundingBox, Detection
from services.use_cases import VisionInferenceRequest, VisionInferenceUseCase


def test_use_case_persists_and_limits_results() -> None:
    detections = [
        Detection(label="part", confidence=0.9, bounding_box=BoundingBox(0, 0, 10, 10), center=(5, 5)),
        Detection(label="tool", confidence=0.8, bounding_box=BoundingBox(10, 10, 20, 20), center=(15, 15)),
    ]
    provider = InMemoryDetectionProvider(detections=detections)
    repository = InMemoryDetectionRepository()
    logger = logging.getLogger("test")
    use_case = VisionInferenceUseCase(provider, repository, logger)

    request = VisionInferenceRequest(selected_labels=["part", "tool"], limit=1)
    response = use_case.execute(request)

    assert response.total == 2
    assert len(response.detections) == 1
    stored = list(repository.list_detections())
    assert list(stored) == detections
