from __future__ import annotations

import threading
from dataclasses import dataclass

from domain.settings.settings import VisionSettings


@dataclass
class UpdateSettingsRequest:
    model_path: str
    camera_index: int
    frame_width: int
    frame_height: int
    target_fps: float
    inference_interval: int
    confidence_threshold: float
    digital_zoom: float
    device: str | None
    selected_labels: tuple[str, ...]


class VisionSettingsStore:
    def __init__(self, initial: VisionSettings) -> None:
        self._settings = initial
        self._lock = threading.RLock()

    def get(self) -> VisionSettings:
        with self._lock:
            return self._settings

    def set(self, new_settings: VisionSettings) -> VisionSettings:
        with self._lock:
            self._settings = new_settings
            return self._settings


class UpdateSettingsUseCase:
    def __init__(self, store: VisionSettingsStore) -> None:
        self._store = store

    def execute(self, request: UpdateSettingsRequest) -> VisionSettings:
        updated = VisionSettings(
            model_path=request.model_path,
            camera_index=request.camera_index,
            frame_width=request.frame_width,
            frame_height=request.frame_height,
            target_fps=request.target_fps,
            inference_interval=request.inference_interval,
            confidence_threshold=request.confidence_threshold,
            digital_zoom=request.digital_zoom,
            device=request.device,
            selected_labels=tuple(request.selected_labels),
        )
        return self._store.set(updated)
