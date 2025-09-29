from __future__ import annotations

import pytest

from domain.settings.settings import VisionSettings


def test_vision_settings_validation() -> None:
    settings = VisionSettings(
        model_path="model.pt",
        camera_index=0,
        frame_width=640,
        frame_height=480,
        target_fps=30.0,
        inference_interval=3,
        confidence_threshold=0.6,
        digital_zoom=1.0,
        device=None,
        selected_labels=(),
    )
    assert settings.frame_width == 640


def test_vision_settings_invalid_frame_width() -> None:
    with pytest.raises(ValueError):
        VisionSettings(
            model_path="model.pt",
            camera_index=0,
            frame_width=0,
            frame_height=480,
            target_fps=30.0,
            inference_interval=3,
            confidence_threshold=0.6,
            digital_zoom=1.0,
            device=None,
            selected_labels=(),
        )
