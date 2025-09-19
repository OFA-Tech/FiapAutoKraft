"""Console application for real-time object detection using YOLO models.

This script provides a lightweight interface to run the same YOLOv12 models
used by the API service directly from the command line. It supports
processing still images, recorded videos and live camera feeds while drawing
bounding boxes and reporting the (x, y) position of each detected object.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Union

import cv2
import numpy as np
from ultralytics import YOLO


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif"}
VIDEO_EXTENSIONS = {
    ".mp4",
    ".avi",
    ".mov",
    ".mkv",
    ".wmv",
    ".mpg",
    ".mpeg",
    ".m4v",
    ".webm",
}


@dataclass
class DetectionBox:
    """Represents a detection bounding box and metadata."""

    label: str
    confidence: float
    top_left: tuple[int, int]
    bottom_right: tuple[int, int]
    center: tuple[int, int]


class ConsoleDetectionApp:
    """Console driven experience for YOLO object detection."""

    def __init__(
        self,
        model_path: Union[str, os.PathLike[str]],
        confidence: float = 0.25,
        iou: float = 0.45,
        max_detections: int = 100,
        device: Optional[str] = None,
        labels_path: Optional[Union[str, os.PathLike[str]]] = None,
    ) -> None:
        self._model_path = Path(model_path)
        self._confidence = max(0.0, min(confidence, 1.0))
        self._iou = max(0.0, min(iou, 1.0))
        self._max_detections = max(1, int(max_detections))
        self._device = device
        self._model = self._load_model()
        self._custom_labels = self._load_custom_labels(labels_path)
        self._class_names = self._resolve_class_names()

    def _load_model(self) -> YOLO:
        if not self._model_path.exists():
            raise FileNotFoundError(
                f"YOLO model weights not found at '{self._model_path}'. "
                "Provide a valid path using --model or YOLOV12_MODEL_PATH."
            )
        model = YOLO(str(self._model_path))
        if self._device:
            try:
                model.to(self._device)
            except Exception as exc:  # pragma: no cover - device availability depends on runtime
                raise RuntimeError(
                    f"Unable to move YOLO model to device '{self._device}'."
                ) from exc
        return model

    def _resolve_class_names(self) -> dict[int, str]:
        if self._custom_labels:
            return self._custom_labels
        names = getattr(self._model, "names", {})
        if isinstance(names, dict):
            return {int(key): str(value) for key, value in names.items()}
        if isinstance(names, (list, tuple)):
            return {index: str(value) for index, value in enumerate(names)}
        return {}

    def _load_custom_labels(
        self, labels_path: Optional[Union[str, os.PathLike[str]]]
    ) -> dict[int, str]:
        """Load custom class labels defined for the keras models."""

        candidates: list[Path] = []
        if labels_path:
            candidates.append(Path(labels_path))

        base_dir = Path(__file__).resolve().parent
        candidates.extend(
            [
                base_dir / "labels.txt",
                base_dir / "keras_models" / "labels.txt",
                base_dir / "keras_models" / "converted_savedmodel" / "labels.txt",
            ]
        )

        selected_path: Optional[Path] = None
        for candidate in candidates:
            if candidate.exists():
                selected_path = candidate
                break

        if selected_path is None:
            return {}

        labels: dict[int, str] = {}
        try:
            with selected_path.open("r", encoding="utf-8") as file:
                for raw_line in file:
                    line = raw_line.strip()
                    if not line:
                        continue

                    parts = line.split(maxsplit=1)
                    if len(parts) == 2 and parts[0].isdigit():
                        labels[int(parts[0])] = parts[1].strip()
                    else:
                        index = len(labels)
                        labels[index] = line
        except OSError:
            return {}

        return labels

    # ------------------------------------------------------------------
    # Public execution helpers
    # ------------------------------------------------------------------
    def run_on_image(self, image_path: Path) -> None:
        frame = cv2.imread(str(image_path))
        if frame is None:
            raise ValueError(f"Unable to read image from '{image_path}'.")

        result = self._predict_frame(frame)
        annotated = self._draw_detections(frame, result)

        window_title = f"YOLO Detection - {image_path.name}"
        cv2.imshow(window_title, annotated)
        print("Press any key in the image window to close...")
        cv2.waitKey(0)
        cv2.destroyWindow(window_title)

    def run_on_video(self, source: Union[str, int]) -> None:
        capture = cv2.VideoCapture(source)
        if not capture.isOpened():
            raise ValueError(
                f"Unable to open video source '{source}'. Make sure the path/index is correct."
            )

        try:
            self._process_stream(capture, title=str(source))
        finally:
            capture.release()
            cv2.destroyAllWindows()

    # ------------------------------------------------------------------
    # Internal processing helpers
    # ------------------------------------------------------------------
    def _process_stream(self, capture: cv2.VideoCapture, title: str) -> None:
        fps_smoothing = 0.9
        fps_value: Optional[float] = None
        window_title = f"YOLO Detection - {title}"

        while True:
            success, frame = capture.read()
            if not success:
                break

            start_time = time.perf_counter()
            result = self._predict_frame(frame)
            annotated = self._draw_detections(frame, result)
            elapsed = time.perf_counter() - start_time
            fps_instant = 1.0 / elapsed if elapsed > 0 else 0.0
            if fps_value is None:
                fps_value = fps_instant
            else:
                fps_value = fps_value * fps_smoothing + fps_instant * (1 - fps_smoothing)

            if fps_value is not None:
                cv2.putText(
                    annotated,
                    f"FPS: {fps_value:.1f}",
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0, 255, 0),
                    2,
                    cv2.LINE_AA,
                )

            cv2.imshow(window_title, annotated)
            key = cv2.waitKey(1) & 0xFF
            if key in {ord("q"), 27}:  # q or ESC
                break

    def _predict_frame(self, frame: np.ndarray):
        results = self._model.predict(
            source=frame,
            conf=self._confidence,
            iou=self._iou,
            max_det=self._max_detections,
            verbose=False,
        )
        if not results:
            raise RuntimeError("YOLO did not return inference results for the provided frame.")
        return results[0]

    def _draw_detections(self, frame: np.ndarray, result) -> np.ndarray:
        output = frame.copy()
        boxes = getattr(result, "boxes", None)
        if boxes is None or boxes.xyxy is None:
            return output

        try:
            xyxy = boxes.xyxy.cpu().numpy()
            confidences = boxes.conf.cpu().numpy() if boxes.conf is not None else []
            class_ids = boxes.cls.cpu().numpy() if boxes.cls is not None else []
        except AttributeError:
            xyxy = boxes.xyxy
            confidences = boxes.conf if boxes.conf is not None else []
            class_ids = boxes.cls if boxes.cls is not None else []

        for idx, coords in enumerate(xyxy):
            x_min, y_min, x_max, y_max = (int(float(value)) for value in coords)
            confidence = float(confidences[idx]) if idx < len(confidences) else 0.0
            class_id = int(class_ids[idx]) if idx < len(class_ids) else -1
            label = self._class_names.get(class_id)
            if self._custom_labels and label is None:
                continue
            if label is None:
                label = str(class_id)

            center_x = int((x_min + x_max) / 2)
            center_y = int((y_min + y_max) / 2)

            self._draw_box(
                output,
                DetectionBox(
                    label=label,
                    confidence=confidence,
                    top_left=(x_min, y_min),
                    bottom_right=(x_max, y_max),
                    center=(center_x, center_y),
                ),
            )
        return output

    @staticmethod
    def _draw_box(frame: np.ndarray, box: DetectionBox) -> None:
        color = (0, 255, 0)
        cv2.rectangle(frame, box.top_left, box.bottom_right, color, 2)
        cv2.circle(frame, box.center, radius=4, color=(0, 0, 255), thickness=-1)

        label = f"{box.label} {box.confidence:.2f}" if box.confidence > 0 else box.label
        position_text = f"({box.center[0]}, {box.center[1]})"

        text = f"{label} {position_text}".strip()
        text_origin = (box.top_left[0], max(box.top_left[1] - 10, 25))
        cv2.putText(
            frame,
            text,
            text_origin,
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )


# ----------------------------------------------------------------------
# CLI entry point helpers
# ----------------------------------------------------------------------

def parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run YOLOv12 object detection on images, videos or a live camera feed.",
    )
    parser.add_argument(
        "--source",
        default="0",
        help=(
            "Path to an image/video file or camera index (default: 0). "
            "Use integers for camera indexes."
        ),
    )
    parser.add_argument(
        "--model",
        default=os.getenv("YOLOV12_MODEL_PATH", "yolov8n.pt"),
        help="Path to the YOLO model weights. Defaults to YOLOV12_MODEL_PATH or 'yolov8n.pt'.",
    )
    parser.add_argument(
        "--confidence",
        type=float,
        default=0.25,
        help="Minimum confidence score required for a detection (default: 0.25).",
    )
    parser.add_argument(
        "--iou",
        type=float,
        default=0.45,
        help="Intersection-over-Union threshold used for non-max suppression (default: 0.45).",
    )
    parser.add_argument(
        "--max-detections",
        type=int,
        default=100,
        help="Maximum number of detections per frame (default: 100).",
    )
    parser.add_argument(
        "--device",
        default=None,
        help="Optional Torch device where the model should run (e.g. 'cuda:0' or 'cpu').",
    )
    parser.add_argument(
        "--labels",
        default=None,
        help=(
            "Optional path to a custom labels.txt file. If not provided, the application "
            "searches the keras_models directory for labels."
        ),
    )
    return parser.parse_args(list(argv) if argv is not None else None)


def interpret_source(raw_source: str) -> Union[int, str]:
    try:
        return int(raw_source)
    except ValueError:
        return raw_source


def determine_source_type(source: Union[int, str]) -> str:
    if isinstance(source, int):
        return "camera"
    suffix = Path(source).suffix.lower()
    if suffix in IMAGE_EXTENSIONS:
        return "image"
    if suffix in VIDEO_EXTENSIONS:
        return "video"
    raise ValueError(
        "Unable to determine the input type. Provide a valid image/video file or camera index."
    )


def main(argv: Optional[Iterable[str]] = None) -> int:
    args = parse_args(argv)
    source = interpret_source(args.source)

    app = ConsoleDetectionApp(
        model_path=args.model,
        confidence=args.confidence,
        iou=args.iou,
        max_detections=args.max_detections,
        device=args.device,
        labels_path=args.labels,
    )

    try:
        source_type = determine_source_type(source)
        if source_type == "image":
            image_path = Path(str(source)).expanduser().resolve()
            if not image_path.exists():
                raise FileNotFoundError(f"Image file '{image_path}' does not exist.")
            app.run_on_image(image_path)
        elif source_type == "video":
            video_path = Path(str(source)).expanduser().resolve()
            if not video_path.exists():
                raise FileNotFoundError(f"Video file '{video_path}' does not exist.")
            app.run_on_video(str(video_path))
        else:
            app.run_on_video(source)
    except KeyboardInterrupt:
        print("\nDetection interrupted by user.")
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    finally:
        cv2.destroyAllWindows()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
