"""Smoke tests for container wiring."""

from __future__ import annotations

from app.container import ApplicationContainer
from services.use_cases import VisionInferenceRequest


def test_container_scope_resolves_use_case() -> None:
    container = ApplicationContainer()
    container.ensure_configured()

    with container.enter_scope("run") as scope:
        use_case = scope.vision_inference_use_case()
        response = use_case.execute(VisionInferenceRequest())

    assert response.total >= 0
    assert len(response.detections) == response.total
