"""Computer vision service module for YOLO-based inference."""

from __future__ import annotations

import time
from dataclasses import dataclass
import logging
from typing import Callable, Iterable, Optional

import cv2
import cvzone
import numpy as np
import torch
from ultralytics import YOLO


@dataclass
class InferenceMetadata:
    """Keep track of metadata that is useful for diagnostics on screen."""

    fps: float = 0.0
    last_inference_ms: float = 0.0
    device: str = "cpu"


def _resolve_device(device: Optional[str]) -> str:
    if device:
        if device == "cuda" and not torch.cuda.is_available():
            raise RuntimeError("CUDA was requested but is not available on this machine.")
        return device
    return "cuda" if torch.cuda.is_available() else "cpu"


def _load_model(model_path: str, device: str) -> YOLO:
    model = YOLO(model_path)
    model.to(device)
    return model


def _warmup_model(model: YOLO, device: str) -> None:
    """Run a quick warmup to stabilise inference time on the selected device."""

    model_args = getattr(model.model, "args", {})
    imgsz = 640
    if isinstance(model_args, dict):
        imgsz = int(model_args.get("imgsz", imgsz))

    dummy = np.zeros((imgsz, imgsz, 3), dtype=np.uint8)
    _ = model.predict(dummy, device=device, verbose=False)


def _configure_camera(args) -> cv2.VideoCapture:
    cap = cv2.VideoCapture(args.camera_index)
    if not cap.isOpened():
        cap = cv2.VideoCapture(args.camera_index, cv2.CAP_V4L2)
    if not cap.isOpened():
        raise RuntimeError(
            f"Unable to open camera index {args.camera_index}. Verify that the device exists."
        )

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.frame_width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.frame_height)
    cap.set(cv2.CAP_PROP_FPS, args.target_fps)
    return cap


def _apply_digital_zoom(frame: np.ndarray, zoom_factor: float) -> np.ndarray:
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


def _normalise_label_names(names) -> list[str]:
    """Normalise any YOLO names structure into a simple list of labels."""

    if isinstance(names, dict):
        return [names[index] for index in sorted(names)]
    if isinstance(names, (list, tuple)):
        return list(names)
    # Fallback: iterate over mapping-like objects preserving values when possible
    try:
        return [value for _, value in sorted(names.items())]
    except AttributeError:
        return [str(names)]


def _draw_bounding_boxes(
    frame: np.ndarray,
    detections: Iterable,
    names: dict[int, str],
    confidence_threshold: float,
    selected_labels: Optional[Iterable[str]] = None,
) -> tuple[np.ndarray, list[dict]]:
    """Draw only boxes with conf >= max(confidence_threshold, 0.75) and return their coordinates."""

    drawn: list[dict] = []
    min_conf = max(confidence_threshold, 0.75)
    allowed = None
    if selected_labels:
        allowed = {label.lower() for label in selected_labels if label}

    for detection in detections:
        boxes = getattr(detection, "boxes", None)
        if boxes is None:
            continue

        for box in boxes:
            conf = float(box.conf[0])
            if conf < min_conf:
                continue

            x1, y1, x2, y2 = map(int, box.xyxy[0])
            cx = (x1 + x2) // 2
            cy = (y1 + y2) // 2
            cls = int(box.cls[0])
            label = names.get(cls, str(cls))
            if allowed is not None and label.lower() not in allowed:
                continue

            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cvzone.putTextRect(
                frame,
                f"{label} {conf:.2f}",
                (x1, max(0, y1 - 10)),
                scale=1,
                thickness=1,
                offset=5,
            )
            cv2.circle(frame, (cx, cy), 4, (0, 0, 255), -1)
            cvzone.putTextRect(
                frame,
                f"({cx}, {cy})",
                (cx + 8, cy - 8),
                scale=0.8,
                thickness=1,
                offset=4,
            )

            drawn.append(
                {
                    "label": label,
                    "conf": conf,
                    "bbox_xyxy": (x1, y1, x2, y2),
                    "center_xy": (cx, cy),
                }
            )
    return frame, drawn


def _annotate_metadata(frame: np.ndarray, metadata: InferenceMetadata) -> np.ndarray:
    text = (
        f"FPS: {metadata.fps:.1f} | Inference: {metadata.last_inference_ms:.1f} ms | Device: {metadata.device}"
    )
    cvzone.putTextRect(frame, text, (10, 30), scale=1, thickness=1, offset=5)
    return frame


class VisionService:
    """Service that encapsulates YOLO-based inference and rendering logic."""

    def __init__(self, args) -> None:
        self.args = args
        self.device = _resolve_device(args.device)
        self.model = _load_model(args.model_path, self.device)
        _warmup_model(self.model, self.device)
        self.names = self.model.names
        self._selected_labels: set[str] | None = None
        self._last_detections: list[dict] = []
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def get_model_labels(self) -> list[str]:
        """Return the human readable class labels available in the loaded model."""

        return _normalise_label_names(self.names)

    @staticmethod
    def discover_model_labels(model_path: str) -> list[str]:
        """Load a YOLO model and return the labels it exposes."""

        model = YOLO(model_path)
        return _normalise_label_names(getattr(model, "names", {}))

    def select_labels(self, labels: Optional[Iterable[str]]) -> None:
        """Select labels that should be drawn and tracked during inference."""

        if labels is None:
            self._selected_labels = None
            return

        available = self.get_model_labels()
        lookup = {label.lower(): label for label in available}
        selected: set[str] = set()
        for label in labels:
            if not label:
                continue
            resolved = lookup.get(label.lower())
            if resolved:
                selected.add(resolved)

        if not selected:
            raise ValueError(
                "None of the provided labels are recognised. Available labels: "
                + ", ".join(available)
            )

        self._selected_labels = selected

    def get_last_detections(self, labels: Optional[Iterable[str]] = None) -> list[dict]:
        """Return coordinates of the most recent detections optionally filtered by label."""

        if not self._last_detections:
            return []

        if labels is None:
            return list(self._last_detections)

        requested = {label.lower() for label in labels if label}
        if not requested:
            return []

        return [
            detection
            for detection in self._last_detections
            if detection["label"].lower() in requested
        ]

    def run(
        self,
        frame_callback: Optional[Callable[[np.ndarray], None]] = None,
        stop_event: Optional["threading.Event"] = None,
    ) -> None:
        cap = _configure_camera(self.args)
        frame_count = 0
        last_inference = None
        metadata = InferenceMetadata(device=self.device)

        try:
            while True:
                if stop_event and stop_event.is_set():
                    break
                loop_start = time.perf_counter()
                ret, frame = cap.read()
                if not ret:
                    self.logger.warning("Unable to read frame from camera. Stopping stream.")
                    break

                frame_count += 1
                if frame_count % max(1, self.args.inference_interval) == 0 or last_inference is None:
                    inference_start = time.perf_counter()
                    with torch.inference_mode():
                        last_inference = self.model.predict(
                            frame,
                            device=self.device,
                            verbose=False,
                            conf=self.args.confidence_threshold,
                        )
                    metadata.last_inference_ms = (time.perf_counter() - inference_start) * 1000

                if last_inference:
                    frame, detections_info = _draw_bounding_boxes(
                        frame,
                        last_inference,
                        self.names,
                        self.args.confidence_threshold,
                        self._selected_labels,
                    )
                    self._last_detections = detections_info
                    for detection in detections_info:
                        self.logger.info(
                            "Detection: %s conf=%.2f bbox=%s center=%s",
                            detection["label"],
                            detection["conf"],
                            detection["bbox_xyxy"],
                            detection["center_xy"],
                        )

                loop_duration = time.perf_counter() - loop_start
                metadata.fps = 1.0 / max(loop_duration, 1e-6)
                frame = _annotate_metadata(frame, metadata)
                frame = _apply_digital_zoom(frame, self.args.digital_zoom)

                if frame_callback is not None:
                    frame_callback(frame)
                else:
                    cv2.imshow(self.args.window_name, frame)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        break
        finally:
            cap.release()
            self._last_detections = []
            if frame_callback is None:
                cv2.destroyAllWindows()
