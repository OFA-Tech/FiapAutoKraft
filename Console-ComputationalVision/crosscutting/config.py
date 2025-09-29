"""Application configuration loading helpers."""

from __future__ import annotations

import os
from dataclasses import dataclass


def _env(key: str, default: str) -> str:
    return os.getenv(f"CCV_{key}", default)


@dataclass(slots=True)
class AppSettings:
    """Container for runtime configuration values.

    Values are read lazily from environment variables with the ``CCV_`` prefix
    so the application remains 12-factor friendly without requiring third-party
    settings libraries.
    """

    model_path: str = _env("MODEL_PATH", "models/best.pt")
    camera_index: int = int(_env("CAMERA_INDEX", "0"))
    frame_width: int = int(_env("FRAME_WIDTH", "1280"))
    frame_height: int = int(_env("FRAME_HEIGHT", "720"))
    target_fps: float = float(_env("TARGET_FPS", "30"))
    inference_interval: int = int(_env("INFERENCE_INTERVAL", "3"))
    confidence_threshold: float = float(_env("CONFIDENCE_THRESHOLD", "0.60"))
    digital_zoom: float = float(_env("DIGITAL_ZOOM", "1.0"))
    device: str | None = os.getenv("CCV_DEVICE")
    log_level: str = _env("LOG_LEVEL", "INFO")


def load_settings() -> AppSettings:
    """Load configuration values from the current environment."""

    return AppSettings()


__all__ = ["AppSettings", "load_settings"]
