from __future__ import annotations

import logging
import time

import numpy as np

from application.start_detection import DetectionController, StartDetectionUseCase, StopDetectionUseCase
from application.update_settings import VisionSettingsStore
from domain.camera.camera import Camera, Frame, Resolution
from domain.camera.camera_repository import CameraRepository
from domain.events import DetectionProduced
from domain.settings.settings import VisionSettings
from domain.vision.detector import Detector
from domain.vision.model import BoundingBox, InferenceResult
from shared.bus import EventBus


class FakeDetectorFactory:
    def __init__(self, detector: Detector) -> None:
        self._detector = detector

    def create(self, *args, **kwargs) -> Detector:
        return self._detector


class FakeCameraRepository(CameraRepository):
    def list_cameras(self):
        return [Camera(identifier="cam", index=0, name="Fake", default_resolution=Resolution(64, 64))]

    def open(self, index: int, resolution: Resolution, target_fps: float):
        return FakeStream()


class FakeStream:
    def __init__(self) -> None:
        self._frames = [np.zeros((64, 64, 3), dtype=np.uint8) for _ in range(3)]
        self._index = 0

    def read(self) -> Frame | None:
        if self._index >= len(self._frames):
            time.sleep(0.05)
            return None
        frame = Frame(data=self._frames[self._index], timestamp=time.time())
        self._index += 1
        return frame

    def close(self) -> None:
        pass


class FakeDetector(Detector):
    def labels(self):
        return ("item",)

    def infer(self, frame: Frame, selected_labels=None, confidence_threshold: float = 0.5) -> InferenceResult:
        bbox = BoundingBox(label="item", confidence=0.9, xyxy=(0, 0, 10, 10), center=(5, 5))
        return InferenceResult(boxes=(bbox,), annotated_frame=frame.data, duration_ms=1.0, fps=0.0)


def test_detection_controller_emits_events() -> None:
    bus: EventBus[DetectionProduced] = EventBus()
    repo = FakeCameraRepository()
    detector = FakeDetector()
    factory = FakeDetectorFactory(detector)
    controller = DetectionController(repo, factory, bus, logging.getLogger("det"))
    settings = VisionSettings(
        model_path="model.pt",
        camera_index=0,
        frame_width=64,
        frame_height=64,
        target_fps=30.0,
        inference_interval=1,
        confidence_threshold=0.5,
        digital_zoom=1.0,
        device=None,
        selected_labels=(),
    )
    store = VisionSettingsStore(settings)
    start_use_case = StartDetectionUseCase(controller, store)
    stop_use_case = StopDetectionUseCase(controller)

    events: list[DetectionProduced] = []
    bus.subscribe("vision.detection", events.append)

    start_use_case.execute()
    timeout = time.time() + 1
    while not events and time.time() < timeout:
        time.sleep(0.05)

    stop_use_case.execute()

    assert events, "Expected detection events"
