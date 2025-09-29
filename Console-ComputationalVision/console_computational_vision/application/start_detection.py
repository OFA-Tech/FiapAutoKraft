from __future__ import annotations

import threading
import time
from dataclasses import dataclass

from ..domain.camera.camera import Frame, Resolution
from ..domain.camera.camera_repository import CameraRepository
from ..domain.events import DetectionProduced, DeviceStateChanged, ErrorRaised
from ..domain.settings.settings import VisionSettings
from ..domain.vision.detector import Detector, DetectorFactory
from ..shared.bus import EventBus
from ..shared.utils import apply_digital_zoom


DETECTION_TOPIC = "vision.detection"
DEVICE_TOPIC = "device.state"
ERROR_TOPIC = "errors"


@dataclass
class DetectionControllerState:
    thread: threading.Thread | None = None
    stop_event: threading.Event | None = None
    running: bool = False


class DetectionController:
    def __init__(
        self,
        camera_repository: CameraRepository,
        detector_factory: DetectorFactory,
        event_bus: EventBus,
        logger,
    ) -> None:
        self._camera_repository = camera_repository
        self._detector_factory = detector_factory
        self._bus = event_bus
        self._logger = logger
        self._state = DetectionControllerState()
        self._lock = threading.RLock()

    def start(self, settings: VisionSettings) -> None:
        with self._lock:
            if self._state.running:
                self._logger.info("Detection already running")
                return

            resolution = Resolution(settings.frame_width, settings.frame_height)
            stream = self._camera_repository.open(
                settings.camera_index,
                resolution,
                settings.target_fps,
            )
            detector = self._detector_factory.create(settings.model_path, settings.device)
            stop_event = threading.Event()
            thread = threading.Thread(
                target=self._run,
                args=(stream, detector, settings, stop_event),
                daemon=True,
                name="DetectionController",
            )
            self._state = DetectionControllerState(thread=thread, stop_event=stop_event, running=True)
            thread.start()
            self._bus.publish(DEVICE_TOPIC, DeviceStateChanged("Detection started"))
            self._logger.info("Detection started")

    def stop(self) -> None:
        with self._lock:
            if not self._state.running:
                return
            assert self._state.stop_event is not None
            self._state.stop_event.set()
            thread = self._state.thread
        if thread:
            thread.join(timeout=5)
        with self._lock:
            self._state = DetectionControllerState()
        self._bus.publish(DEVICE_TOPIC, DeviceStateChanged("Detection stopped"))
        self._logger.info("Detection stopped")

    def _run(
        self,
        stream,
        detector: Detector,
        settings: VisionSettings,
        stop_event: threading.Event,
    ) -> None:
        frame_counter = 0
        last_result = None
        try:
            while not stop_event.is_set():
                frame = stream.read()
                if frame is None:
                    time.sleep(0.01)
                    continue

                frame_counter += 1
                loop_start = time.perf_counter()
                processed = apply_digital_zoom(frame.data, settings.digital_zoom)
                working_frame = Frame(data=processed, timestamp=frame.timestamp)

                perform_inference = (
                    frame_counter % max(1, settings.inference_interval) == 0
                    or last_result is None
                )
                if perform_inference:
                    try:
                        last_result = detector.infer(
                            working_frame,
                            selected_labels=settings.selected_labels,
                            confidence_threshold=settings.confidence_threshold,
                        )
                    except Exception as exc:
                        self._logger.exception("Detector failed", exc_info=exc)
                        self._bus.publish(ERROR_TOPIC, ErrorRaised("Detector failure", exc))
                        continue

                if last_result is None:
                    continue

                annotated = Frame(data=last_result.annotated_frame, timestamp=frame.timestamp)
                duration = (time.perf_counter() - loop_start)
                fps = 1.0 / max(duration, 1e-6)
                event = DetectionProduced(
                    frame=annotated,
                    boxes=last_result.boxes,
                    fps=fps,
                    inference_ms=last_result.duration_ms,
                )
                self._bus.publish(DETECTION_TOPIC, event)
        finally:
            try:
                stream.close()
            except Exception:
                self._logger.exception("Failed to close camera stream")
            with self._lock:
                self._state = DetectionControllerState()
            self._bus.publish(DEVICE_TOPIC, DeviceStateChanged("Detection stopped"))


class StartDetectionUseCase:
    def __init__(self, controller: DetectionController, settings_store) -> None:
        self._controller = controller
        self._settings_store = settings_store

    def execute(self) -> None:
        settings: VisionSettings = self._settings_store.get()
        self._controller.start(settings)


class StopDetectionUseCase:
    def __init__(self, controller: DetectionController) -> None:
        self._controller = controller

    def execute(self) -> None:
        self._controller.stop()
