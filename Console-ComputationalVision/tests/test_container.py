"""Smoke tests for container wiring."""

from __future__ import annotations

from app.container import ApplicationContainer
from services.use_cases import VisionInferenceRequest


def test_container_resolves_use_case() -> None:
    container = ApplicationContainer()
    container.logging()

    with container.enter_scope("run"):
        use_case = container.vision_inference_use_case()
        response = use_case.execute(VisionInferenceRequest())

    assert response.total >= 0
    assert len(response.detections) == response.total
