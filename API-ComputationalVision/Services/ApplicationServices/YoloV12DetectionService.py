import asyncio
import base64
import os
import tempfile
import threading
from pathlib import Path
from binascii import Error as BinasciiError
from typing import Optional, Union

import cv2
import numpy as np
from ultralytics import YOLO

from Domain.Models.Vision.DetectionModel import DetectionModel
from Domain.Models.Vision.BoundingBoxModel import BoundingBoxModel
from Domain.Models.Vision.FrameDetectionsModel import FrameDetectionsModel
from Domain.Models.Vision.ImageDetectionResponseModel import ImageDetectionResponseModel
from Domain.Models.Vision.VideoDetectionResponseModel import VideoDetectionResponseModel


class YoloV12DetectionService:
    """Service responsible for executing YOLOv12 detections over images and videos."""

    def __init__(
        self,
        model_path: Optional[str] = None,
        confidence_threshold: float = 0.25,
        iou_threshold: float = 0.45,
        max_detections: int = 100,
        video_max_frames: int = 60,
        frame_interval: int = 5,
    ) -> None:
        self._model_path = model_path or os.getenv("YOLOV12_MODEL_PATH", "yolov8n.pt")
        self._confidence_threshold = confidence_threshold
        self._iou_threshold = iou_threshold
        self._max_detections = max(1, max_detections)
        self._video_max_frames = max(1, video_max_frames)
        self._frame_interval = max(1, frame_interval)
        self._model: Optional[YOLO] = None
        self._model_lock = threading.Lock()
        self._model_version = Path(self._model_path).stem or "yolov12"

    async def detect_image(self, image_data: Union[bytes, str]) -> ImageDetectionResponseModel:
        """Execute object detection on image payloads provided as bytes or base64 strings."""
        image_bytes = self._normalize_input_bytes(image_data, "image")

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._detect_image_sync, image_bytes)

    async def detect_video(
        self,
        video_data: Union[bytes, str],
        frame_interval: Optional[int] = None,
        max_frames: Optional[int] = None,
    ) -> VideoDetectionResponseModel:
        """Execute object detection on video payloads provided as bytes or base64 strings."""
        video_bytes = self._normalize_input_bytes(video_data, "video")

        interval = max(1, frame_interval or self._frame_interval)
        frame_limit = max(1, max_frames or self._video_max_frames)

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._detect_video_sync, video_bytes, interval, frame_limit)

    #region Private helpers
    def _detect_image_sync(self, image_bytes: bytes) -> ImageDetectionResponseModel:
        frame = self._decode_image(image_bytes)
        result = self._predict_frame(frame)
        detections = self._map_detections(result)
        inference_time_ms = self._compute_inference_time(result)
        return ImageDetectionResponseModel(
            model_version=self._model_version,
            inference_time_ms=inference_time_ms,
            detections=detections,
        )

    def _detect_video_sync(self, video_bytes: bytes, frame_interval: int, frame_limit: int) -> VideoDetectionResponseModel:
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_file:
            temp_file.write(video_bytes)
            temp_path = temp_file.name

        capture = None
        try:
            capture = cv2.VideoCapture(temp_path)
            if not capture.isOpened():
                raise ValueError("Unable to decode the provided video stream. Ensure the file is a valid video.")

            total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
            processed_frames: list[FrameDetectionsModel] = []
            total_inference_time = 0.0
            frame_index = 0
            processed_count = 0

            while processed_count < frame_limit:
                success, frame = capture.read()
                if not success:
                    break

                if frame_index % frame_interval == 0:
                    result = self._predict_frame(frame)
                    detections = self._map_detections(result)
                    processed_frames.append(
                        FrameDetectionsModel(
                            frame_index=frame_index,
                            detections=detections,
                        )
                    )
                    total_inference_time += self._compute_inference_time(result)
                    processed_count += 1

                frame_index += 1

            if not processed_frames:
                raise ValueError("No frames were processed from the provided video.")

            frame_count = total_frames if total_frames > 0 else frame_index
            return VideoDetectionResponseModel(
                model_version=self._model_version,
                frame_count=int(frame_count),
                processed_frames=len(processed_frames),
                frame_interval=frame_interval,
                inference_time_ms=total_inference_time,
                frames=processed_frames,
            )
        finally:
            if capture is not None:
                capture.release()
            try:
                os.remove(temp_path)
            except OSError:
                pass

    def _decode_image(self, image_bytes: bytes) -> np.ndarray:
        np_array = np.frombuffer(image_bytes, dtype=np.uint8)
        if np_array.size == 0:
            raise ValueError("The uploaded image is empty or corrupted.")

        frame = cv2.imdecode(np_array, cv2.IMREAD_COLOR)
        if frame is None:
            raise ValueError("Unable to decode the provided image. Ensure a valid image format is used.")
        return frame

    def _predict_frame(self, frame: np.ndarray):
        model = self._ensure_model_loaded()
        results = model.predict(
            source=frame,
            conf=self._confidence_threshold,
            iou=self._iou_threshold,
            max_det=self._max_detections,
            verbose=False,
        )
        if not results:
            raise RuntimeError("The YOLO model did not return any prediction results.")
        return results[0]

    def _ensure_model_loaded(self) -> YOLO:
        if self._model is not None:
            return self._model

        with self._model_lock:
            if self._model is None:
                try:
                    self._model = YOLO(self._model_path)
                    if getattr(self._model, "ckpt_path", None):
                        self._model_version = Path(str(self._model.ckpt_path)).stem or self._model_version
                except Exception as exc:  # pragma: no cover - defensive
                    raise RuntimeError(
                        f"Unable to load YOLOv12 weights from '{self._model_path}'. "
                        "Confirm the model file exists or provide YOLOV12_MODEL_PATH."
                    ) from exc
        return self._model

    def _map_detections(self, result) -> list[DetectionModel]:
        detections: list[DetectionModel] = []
        boxes = getattr(result, "boxes", None)
        if boxes is None:
            return detections

        names = getattr(result, "names", None)
        if not names:
            model = self._ensure_model_loaded()
            names = getattr(model, "names", {})

        for box in boxes:
            if box.conf is None or box.cls is None or box.xyxy is None:
                continue

            confidence = float(box.conf[0])
            if confidence < self._confidence_threshold:
                continue

            class_id = int(box.cls[0])
            if isinstance(names, dict):
                label = names.get(class_id, str(class_id))
            elif isinstance(names, (list, tuple)) and 0 <= class_id < len(names):
                label = names[class_id]
            else:
                label = str(class_id)
            coordinates = box.xyxy[0].tolist()

            detections.append(
                DetectionModel(
                    class_name=label,
                    confidence=confidence,
                    bounding_box=BoundingBoxModel(
                        xmin=float(coordinates[0]),
                        ymin=float(coordinates[1]),
                        xmax=float(coordinates[2]),
                        ymax=float(coordinates[3]),
                    ),
                )
            )

            if len(detections) >= self._max_detections:
                break

        return detections

    @staticmethod
    def _compute_inference_time(result) -> float:
        speed = getattr(result, "speed", None)
        if isinstance(speed, dict):
            return float(sum(float(value) for value in speed.values()))
        if isinstance(speed, (int, float)):
            return float(speed)
        return 0.0

    def _normalize_input_bytes(self, data: Union[bytes, str], payload_type: str) -> bytes:
        """Decode base64 strings and validate payloads before inference."""
        if isinstance(data, bytes):
            payload = data
        elif isinstance(data, str):
            stripped = data.strip()
            if not stripped:
                raise ValueError(f"No {payload_type} content received for detection.")

            if stripped.lower().startswith("data:"):
                parts = stripped.split(",", 1)
                if len(parts) != 2:
                    raise ValueError(
                        f"The provided {payload_type} content is not a valid base64 data URI.",
                    )
                stripped = parts[1]

            normalized = "".join(stripped.split())
            if not normalized:
                raise ValueError(f"No {payload_type} content received for detection.")

            normalized = normalized.replace("-", "+").replace("_", "/")
            padding = len(normalized) % 4
            if padding:
                normalized += "=" * (4 - padding)

            try:
                payload = base64.b64decode(normalized, validate=True)
            except (BinasciiError, ValueError) as exc:
                raise ValueError(
                    f"The provided {payload_type} content is not valid base64 data.",
                ) from exc
        else:  # pragma: no cover - defensive programming
            raise ValueError(f"Unsupported {payload_type} payload type: {type(data)!r}.")

        if not payload:
            raise ValueError(f"No {payload_type} content received for detection.")

        return payload

    #endregion
