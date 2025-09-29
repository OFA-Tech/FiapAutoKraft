"""Application entry point exposing CLI and GUI experiences."""

from __future__ import annotations

import argparse
import tkinter as tk
from typing import Sequence

from app.container import ApplicationContainer
from app.gui.main_window import VisionApp
from services.use_cases import VisionInferenceRequest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Console Computational Vision runner")
    parser.add_argument("--labels", nargs="*", help="Optional label filters", default=None)
    parser.add_argument("--limit", type=int, default=None, help="Limit console output detections")
    parser.add_argument("--use-yolo", action="store_true", help="Use the YOLO backend (requires dependencies)")
    parser.add_argument(
        "--cli",
        action="store_true",
        help="Run in CLI mode instead of launching the Tkinter interface.",
    )
    return parser


def _run_cli(container: ApplicationContainer, args: argparse.Namespace) -> int:
    if args.use_yolo:
        container.use_yolo_backend()
    container.ensure_configured()

    labels = args.labels if args.labels else None
    with container.enter_scope("run") as scope:
        use_case = scope.vision_inference_use_case()
        response = use_case.execute(
            VisionInferenceRequest(selected_labels=labels, limit=args.limit)
        )
    for detection in response.detections:
        bbox = detection.bounding_box.as_tuple()
        print(
            f"label={detection.label} conf={detection.confidence:.2f} "
            f"bbox={bbox} center={detection.center}"
        )
    print(f"total_detections={response.total}")
    return 0


def _run_gui(container: ApplicationContainer, args: argparse.Namespace) -> int:
    if args.use_yolo:
        container.use_yolo_backend()
    root = tk.Tk()
    VisionApp(root, container, initial_labels=args.labels)
    root.mainloop()
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    container = ApplicationContainer()
    if args.cli:
        return _run_cli(container, args)
    return _run_gui(container, args)


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
