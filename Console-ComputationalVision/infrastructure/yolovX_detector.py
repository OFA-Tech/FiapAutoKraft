from __future__ import annotations

import time
from typing import Iterable

import cv2
import cvzone
import numpy as np
import torch
from ultralytics import YOLO

from domain.camera.camera import Frame
from domain.vision.detector import Detector, DetectorFactory
from domain.vision.model import BoundingBox, InferenceResult
from shared.errors import InfrastructureError


def _normalise_label_names(names) -> list[str]:
    if isinstance(names, dict):
        return [names[index] for index in sorted(names)]
    if isinstance(names, (list, tuple)):
        return list(names)
    try:
        return [value for _, value in sorted(names.items())]
    except AttributeError:
        return [str(names)]


class YoloVxDetector(Detector):
    def __init__(self, model_path: str, device: str | None, logger) -> None:
        self._model_path = model_path
        self._device = device or self._resolve_device()
        try:
            self._model = YOLO(model_path)
        except Exception as exc:
            raise InfrastructureError(f"Unable to load model {model_path}") from exc
        self._model.to(self._device)
        self._labels = _normalise_label_names(getattr(self._model, "names", {}))
        self._logger = logger
        self._warmup()

    def _resolve_device(self) -> str:
        return "cuda" if torch.cuda.is_available() else "cpu"

    def _warmup(self) -> None:
        model_args = getattr(self._model.model, "args", {})
        imgsz = 640
        if isinstance(model_args, dict):
            imgsz = int(model_args.get("imgsz", imgsz))
        dummy = np.zeros((imgsz, imgsz, 3), dtype=np.uint8)
        with torch.inference_mode():
            _ = self._model.predict(dummy, device=self._device, verbose=False)

    def labels(self) -> Iterable[str]:
        return tuple(self._labels)

    def infer(
        self,
        frame: Frame,
        selected_labels: Iterable[str] | None = None,
        confidence_threshold: float = 0.5,
    ) -> InferenceResult:
        with torch.inference_mode():
            start = time.perf_counter()
            results = self._model.predict(
                frame.data,
                device=self._device,
                verbose=False,
                conf=confidence_threshold,
            )
            inference_ms = (time.perf_counter() - start) * 1000

        allowed = None
        if selected_labels:
            allowed = {label.lower() for label in selected_labels}

        annotated = frame.data.copy()
        boxes: list[BoundingBox] = []
        min_conf = max(confidence_threshold, 0.75)
        for result in results:
            predictions = getattr(result, "boxes", None)
            if predictions is None:
                continue
            for prediction in predictions:
                conf = float(prediction.conf[0])
                if conf < min_conf:
                    continue
                x1, y1, x2, y2 = map(int, prediction.xyxy[0])
                cx = (x1 + x2) // 2
                cy = (y1 + y2) // 2
                cls = int(prediction.cls[0])
                label = self._labels[cls] if cls < len(self._labels) else str(cls)
                if allowed and label.lower() not in allowed:
                    continue
                cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cvzone.putTextRect(
                    annotated,
                    f"{label} {conf:.2f}",
                    (x1, max(0, y1 - 10)),
                    scale=1,
                    thickness=1,
                    offset=5,
                )
                cv2.circle(annotated, (cx, cy), 4, (0, 0, 255), -1)
                cvzone.putTextRect(
                    annotated,
                    f"({cx}, {cy})",
                    (cx + 8, cy - 8),
                    scale=0.8,
                    thickness=1,
                    offset=4,
                )
                boxes.append(
                    BoundingBox(
                        label=label,
                        confidence=conf,
                        xyxy=(x1, y1, x2, y2),
                        center=(cx, cy),
                    )
                )
                self._logger.info(
                    "Detection: %s conf=%.2f bbox=%s center=%s",
                    label,
                    conf,
                    (x1, y1, x2, y2),
                    (cx, cy),
                )
        return InferenceResult(boxes=tuple(boxes), annotated_frame=annotated, duration_ms=inference_ms, fps=0.0)


class YoloDetectorFactory(DetectorFactory):
    def __init__(self, logger) -> None:
        self._logger = logger

    def create(self, model_path: str, device: str | None = None) -> Detector:
        return YoloVxDetector(model_path, device, self._logger)
