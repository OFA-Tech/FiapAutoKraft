from __future__ import annotations

import time
from pathlib import Path

import cv2

from domain.camera.camera import Camera, Frame, Resolution
from domain.camera.camera_repository import CameraRepository
from shared.errors import InfrastructureError


class OpenCvCameraStream:
    def __init__(self, capture: cv2.VideoCapture) -> None:
        self._capture = capture

    def read(self) -> Frame | None:
        ret, frame = self._capture.read()
        if not ret:
            return None
        return Frame(data=frame, timestamp=time.time())

    def close(self) -> None:
        self._capture.release()


class OpenCvCameraRepository(CameraRepository):
    def __init__(self, logger, max_devices: int = 10) -> None:
        self._logger = logger
        self._max_devices = max_devices

    def list_cameras(self):
        cameras: list[Camera] = []
        for index in range(self._max_devices):
            capture = cv2.VideoCapture(index)
            if not capture.isOpened():
                capture.release()
                backend = getattr(cv2, "CAP_V4L2", None)
                if backend is not None:
                    capture = cv2.VideoCapture(index, backend)
            if not capture.isOpened():
                capture.release()
                continue
            width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
            height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
            backend_name = ""
            getter = getattr(capture, "getBackendName", None)
            if callable(getter):
                try:
                    backend_name = getter()
                except Exception:
                    backend_name = ""
            capture.release()

            name = self._resolve_camera_name(index)
            cameras.append(
                Camera(
                    identifier=f"camera-{index}",
                    index=index,
                    name=name,
                    backend=backend_name or None,
                    default_resolution=Resolution(width or 0, height or 0),
                )
            )
        return cameras

    def open(self, index: int, resolution: Resolution, target_fps: float):
        capture = cv2.VideoCapture(index)
        if not capture.isOpened():
            backend = getattr(cv2, "CAP_V4L2", None)
            if backend is not None:
                capture = cv2.VideoCapture(index, backend)
        if not capture.isOpened():
            raise InfrastructureError(f"Unable to open camera index {index}")

        capture.set(cv2.CAP_PROP_FRAME_WIDTH, resolution.width)
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, resolution.height)
        capture.set(cv2.CAP_PROP_FPS, target_fps)
        return OpenCvCameraStream(capture)

    def _resolve_camera_name(self, index: int) -> str:
        sysfs_name = Path(f"/sys/class/video4linux/video{index}/name")
        if sysfs_name.exists():
            try:
                return sysfs_name.read_text(encoding="utf-8").strip()
            except OSError:
                pass
        return f"Camera {index}"
