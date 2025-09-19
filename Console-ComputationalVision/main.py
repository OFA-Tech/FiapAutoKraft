from __future__ import annotations

import argparse
import time
from dataclasses import dataclass
from typing import Iterable, Optional

import cv2
import numpy as np
import torch
from ultralytics import YOLO
import cvzone


@dataclass
class InferenceMetadata:
    """Keep track of metadata that is useful for diagnostics on screen."""

    fps: float = 0.0
    last_inference_ms: float = 0.0
    device: str = "cpu"


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="YOLOv12 console runner.")
    parser.add_argument(
        "--model-path",
        default="models/coke_latest.pt",
        help="Path to the YOLOv12 weights to be used for inference.",
    )
    parser.add_argument(
        "--camera-index",
        type=int,
        default=1,
        help="Index of the video capture device (0 for the first camera).",
    )
    parser.add_argument(
        "--frame-width",
        type=int,
        default=1280,
        help="Desired capture width. Use the native camera resolution when possible.",
    )
    parser.add_argument(
        "--frame-height",
        type=int,
        default=720,
        help="Desired capture height. Use the native camera resolution when possible.",
    )
    parser.add_argument(
        "--target-fps",
        type=float,
        default=30.0,
        help="Hint for the camera FPS. Some webcams might ignore this setting.",
    )
    parser.add_argument(
        "--inference-interval",
        type=int,
        default=3,
        help="Run a full YOLO inference every N frames to save resources.",
    )
    parser.add_argument(
        "--confidence-threshold",
        type=float,
        default=0.70,
        help="Minimum confidence value required to draw a bounding box.",
    )
    parser.add_argument(
        "--digital-zoom",
        type=float,
        default=1.0,
        help=(
            "Apply a digital zoom to the displayed frame. Values < 1.0 zoom out, "
            "values > 1.0 zoom in. The inference always runs on the original frame."
        ),
    )
    parser.add_argument(
        "--device",
        choices=("cpu", "cuda"),
        default=None,
        help="Manually select the inference device. Defaults to CUDA when available.",
    )
    parser.add_argument(
        "--window-name",
        default="YOLOv12 Detection",
        help="Title of the OpenCV preview window.",
    )
    return parser.parse_args()


def resolve_device(device: Optional[str]) -> str:
    if device:
        if device == "cuda" and not torch.cuda.is_available():
            raise RuntimeError("CUDA was requested but is not available on this machine.")
        return device
    return "cuda" if torch.cuda.is_available() else "cpu"


def load_model(model_path: str, device: str) -> YOLO:
    model = YOLO(model_path)
    model.to(device)
    return model


def warmup_model(model: YOLO, device: str) -> None:
    """Run a quick warmup to stabilise inference time on the selected device."""

    model_args = getattr(model.model, "args", {})
    imgsz = 640
    if isinstance(model_args, dict):
        imgsz = int(model_args.get("imgsz", imgsz))

    dummy = np.zeros((imgsz, imgsz, 3), dtype=np.uint8)
    _ = model.predict(dummy, device=device, verbose=False)


def configure_camera(args: argparse.Namespace) -> cv2.VideoCapture:
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


def apply_digital_zoom(frame: np.ndarray, zoom_factor: float) -> np.ndarray:
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


def draw_bounding_boxes(
    frame: np.ndarray,
    detections: Iterable,
    names: dict[int, str],
    confidence_threshold: float,
) -> tuple[np.ndarray, list[dict]]:
    """Draw only boxes with conf >= max(confidence_threshold, 0.75)
    and return their coordinates."""
    drawn: list[dict] = []
    min_conf = max(confidence_threshold, 0.75)

    for detection in detections:
        boxes = getattr(detection, "boxes", None)
        if boxes is None:
            continue

        for box in boxes:
            conf = float(box.conf[0])
            if conf < min_conf:
                continue

            x1, y1, x2, y2 = map(int, box.xyxy[0])   # top-left & bottom-right
            cx = (x1 + x2) // 2                      # center (x, y)
            cy = (y1 + y2) // 2
            cls = int(box.cls[0])
            label = names.get(cls, str(cls))

            # rectangle + label
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cvzone.putTextRect(
                frame,
                f"{label} {conf:.2f}",
                (x1, max(0, y1 - 10)),
                scale=1,
                thickness=1,
                offset=5,
            )
            # (optional) draw the center and show coordinates
            cv2.circle(frame, (cx, cy), 4, (0, 0, 255), -1)
            cvzone.putTextRect(
                frame,
                f"({cx}, {cy})",
                (cx + 8, cy - 8),
                scale=0.8,
                thickness=1,
                offset=4,
            )

            drawn.append({
                "label": label,
                "conf": conf,
                "bbox_xyxy": (x1, y1, x2, y2),
                "center_xy": (cx, cy),
            })
    return frame, drawn


def annotate_metadata(frame: np.ndarray, metadata: InferenceMetadata) -> np.ndarray:
    text = f"FPS: {metadata.fps:.1f} | Inference: {metadata.last_inference_ms:.1f} ms | Device: {metadata.device}"
    cvzone.putTextRect(frame, text, (10, 30), scale=1, thickness=1, offset=5)
    return frame


def main() -> int:
    args = parse_arguments()
    device = resolve_device(args.device)
    model = load_model(args.model_path, device)
    warmup_model(model, device)
    names = model.names

    cap = configure_camera(args)
    frame_count = 0
    last_inference = None
    metadata = InferenceMetadata(device=device)

    try:
        while True:
            loop_start = time.perf_counter()
            ret, frame = cap.read()
            if not ret:
                print("[WARN] Unable to read frame from camera. Stopping stream.")
                break

            frame_count += 1
            if frame_count % max(1, args.inference_interval) == 0 or last_inference is None:
                inference_start = time.perf_counter()
                with torch.inference_mode():
                    last_inference = model.predict(
                        frame, device=device, verbose=False, conf=args.confidence_threshold
                    )
                metadata.last_inference_ms = (time.perf_counter() - inference_start) * 1000

            if last_inference:
                frame, detections_info = draw_bounding_boxes(
                    frame, last_inference, names, args.confidence_threshold
                )
                for d in detections_info:
                    print(d["label"], d["conf"], d["bbox_xyxy"], d["center_xy"])

            loop_duration = time.perf_counter() - loop_start
            metadata.fps = 1.0 / max(loop_duration, 1e-6)
            frame = annotate_metadata(frame, metadata)
            frame = apply_digital_zoom(frame, args.digital_zoom)

            cv2.imshow(args.window_name, frame)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
