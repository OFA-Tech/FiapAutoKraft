from __future__ import annotations

import argparse

from services.vision_service import VisionService


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="YOLOv12 console runner.")
    parser.add_argument(
        "--model-path",
        default="models/best.pt",
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
        default=0.60,
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


def main() -> int:
    args = parse_arguments()
    service = VisionService(args)
    service.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
