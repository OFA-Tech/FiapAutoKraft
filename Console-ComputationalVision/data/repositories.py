"""Data layer abstractions and in-memory implementations."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Iterable, List, MutableSequence, Protocol, Sequence

from domain.entities import BoundingBox, Detection, DetectionBatch


class DetectionProvider(Protocol):
    """Provides detection results from an inference backend."""

    def run_inference(self, *, selected_labels: Sequence[str] | None = None) -> DetectionBatch:
        """Execute inference and return a batch of detections."""


class DetectionResultRepository(Protocol):
    """Persistence boundary for inference results."""

    def store(self, batch: DetectionBatch) -> None:
        """Persist the batch for later retrieval."""

    def list_detections(self) -> Sequence[Detection]:
        """Return the most recently persisted detections."""

    def clear(self) -> None:
        """Remove all stored detections."""


@dataclass
class InMemoryDetectionRepository(DetectionResultRepository):
    """Simple in-memory repository used for tests and development."""

    _batches: MutableSequence[DetectionBatch] = field(default_factory=list)

    def store(self, batch: DetectionBatch) -> None:
        self._batches.append(batch)

    def list_detections(self) -> Sequence[Detection]:
        if not self._batches:
            return []
        return self._batches[-1].detections

    def clear(self) -> None:
        self._batches.clear()


@dataclass
class InMemoryDetectionProvider(DetectionProvider):
    """Deterministic provider returning preconfigured detections."""

    detections: Sequence[Detection] | None = None

    def run_inference(self, *, selected_labels: Sequence[str] | None = None) -> DetectionBatch:
        pool = list(self.detections or _default_sample_detections())
        if selected_labels:
            wanted = {label.lower() for label in selected_labels}
            pool = [d for d in pool if d.label.lower() in wanted]
        return DetectionBatch(detections=pool, frame_timestamp=time.monotonic())


class YoloDetectionProvider(DetectionProvider):
    """YOLO-backed provider that mirrors the responsibilities of the legacy ``VisionService``."""

    def __init__(
        self,
        *,
        model_path: str,
        camera_index: int,
        frame_width: int,
        frame_height: int,
        target_fps: float,
        inference_interval: int,
        confidence_threshold: float,
        digital_zoom: float,
        device: str | None,
    ) -> None:
        self.model_path = model_path
        self.camera_index = camera_index
        self.frame_width = frame_width
        self.frame_height = frame_height
        self.target_fps = target_fps
        self.inference_interval = inference_interval
        self.confidence_threshold = confidence_threshold
        self.digital_zoom = digital_zoom
        self.device_override = device
        self._model = None
        self._names: List[str] | None = None
        self._device: str | None = None

    # The heavy libraries are imported lazily within the helper methods so that
    # tests can run without installing the full vision stack.

    def _resolve_device(self) -> str:
        import torch  # type: ignore[import-not-found]

        if self.device_override:
            if self.device_override == "cuda" and not torch.cuda.is_available():
                msg = "CUDA was requested but is not available on this machine."
                raise RuntimeError(msg)
            return self.device_override
        return "cuda" if torch.cuda.is_available() else "cpu"

    def _load_model(self) -> None:
        from ultralytics import YOLO  # type: ignore[import-not-found]

        if self._model is None:
            device = self._resolve_device()
            model = YOLO(self.model_path)
            model.to(device)
            self._model = model
            self._device = device
            names = getattr(model, "names", {})
            self._names = self._normalise_label_names(names)
            self._warmup_model(model, device)

    @staticmethod
    def _warmup_model(model, device: str) -> None:
        import numpy as np  # type: ignore[import-not-found]

        model_args = getattr(model.model, "args", {})
        imgsz = 640
        if isinstance(model_args, dict):
            imgsz = int(model_args.get("imgsz", imgsz))
        dummy = np.zeros((imgsz, imgsz, 3), dtype=np.uint8)
        model.predict(dummy, device=device, verbose=False)

    @staticmethod
    def _normalise_label_names(names) -> List[str]:
        if isinstance(names, dict):
            return [names[index] for index in sorted(names)]
        if isinstance(names, (list, tuple)):
            return list(names)
        try:
            return [value for _, value in sorted(names.items())]
        except AttributeError:  # pragma: no cover - defensive fall-back
            return [str(names)]

    def _configure_camera(self):
        import cv2  # type: ignore[import-not-found]

        cap = cv2.VideoCapture(self.camera_index)
        if not cap.isOpened():
            cap = cv2.VideoCapture(self.camera_index, cv2.CAP_V4L2)
        if not cap.isOpened():  # pragma: no cover - hardware dependent
            msg = f"Unable to open camera index {self.camera_index}."
            raise RuntimeError(msg)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.frame_width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.frame_height)
        cap.set(cv2.CAP_PROP_FPS, self.target_fps)
        return cap

    @staticmethod
    def _apply_digital_zoom(frame, zoom_factor: float):
        import cv2  # type: ignore[import-not-found]
        import numpy as np  # type: ignore[import-not-found]

        if np.isclose(zoom_factor, 1.0):
            return frame
        height, width = frame.shape[:2]
        if zoom_factor < 1.0:
            new_width = max(1, int(width * zoom_factor))
            new_height = max(1, int(height * zoom_factor))
            resized = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_AREA)
            canvas = np.zeros_like(frame)
            x_offset = (width - new_width) // 2
            y_offset = (height - new_height) // 2
            canvas[y_offset : y_offset + new_height, x_offset : x_offset + new_width] = resized
            return canvas
        crop_width = max(1, int(width / zoom_factor))
        crop_height = max(1, int(height / zoom_factor))
        x_start = max(0, (width - crop_width) // 2)
        y_start = max(0, (height - crop_height) // 2)
        cropped = frame[y_start : y_start + crop_height, x_start : x_start + crop_width]
        return cv2.resize(cropped, (width, height), interpolation=cv2.INTER_LINEAR)

    def run_inference(self, *, selected_labels: Sequence[str] | None = None) -> DetectionBatch:
        """Execute inference similar to the legacy ``VisionService.run`` loop."""

        import cv2  # type: ignore[import-not-found]
        import numpy as np  # type: ignore[import-not-found]
        import torch  # type: ignore[import-not-found]
        import cvzone  # type: ignore[import-not-found]

        self._load_model()
        assert self._model is not None  # For type-checkers
        assert self._names is not None
        assert self._device is not None

        cap = self._configure_camera()
        metadata = {"device": self._device}
        detections: List[Detection] = []
        frame_timestamp = time.monotonic()

        try:
            ret, frame = cap.read()
            if not ret:  # pragma: no cover - hardware dependent
                msg = "Unable to read frame from camera."
                raise RuntimeError(msg)
            with torch.inference_mode():
                results = self._model.predict(
                    frame,
                    device=self._device,
                    verbose=False,
                    conf=self.confidence_threshold,
                )
            names_lookup = {index: name for index, name in enumerate(self._names)}
            allowed = {label.lower() for label in selected_labels} if selected_labels else None
            for result in results:
                boxes = getattr(result, "boxes", None)
                if boxes is None:
                    continue
                for box in boxes:
                    conf = float(box.conf[0])
                    if conf < self.confidence_threshold:
                        continue
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    cls = int(box.cls[0])
                    label = names_lookup.get(cls, str(cls))
                    if allowed and label.lower() not in allowed:
                        continue
                    cx = (x1 + x2) // 2
                    cy = (y1 + y2) // 2
                    detections.append(
                        Detection(
                            label=label,
                            confidence=conf,
                            bounding_box=BoundingBox(x1=x1, y1=y1, x2=x2, y2=y2),
                            center=(cx, cy),
                        )
                    )
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cvzone.putTextRect(frame, f"{label} {conf:.2f}", (x1, max(0, y1 - 10)))
            frame = self._apply_digital_zoom(frame, self.digital_zoom)
            _ = metadata  # Placeholder for future metadata enrichment.
        finally:
            cap.release()
            cv2.destroyAllWindows()

        return DetectionBatch(detections=detections, frame_timestamp=frame_timestamp)


def _default_sample_detections() -> List[Detection]:
    return [
        Detection(
            label="part",
            confidence=0.95,
            bounding_box=BoundingBox(x1=100, y1=120, x2=220, y2=260),
            center=(160, 190),
        ),
        Detection(
            label="tool",
            confidence=0.88,
            bounding_box=BoundingBox(x1=300, y1=340, x2=420, y2=480),
            center=(360, 410),
        ),
    ]


__all__ = [
    "DetectionProvider",
    "DetectionResultRepository",
    "InMemoryDetectionRepository",
    "InMemoryDetectionProvider",
    "YoloDetectionProvider",
]
