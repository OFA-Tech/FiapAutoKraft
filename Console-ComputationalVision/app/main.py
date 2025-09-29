"""Console entry point for running the vision inference use case."""

from __future__ import annotations

import argparse
from typing import Sequence

from app.container import ApplicationContainer, use_yolo_provider
from services.use_cases import VisionInferenceRequest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the computational vision pipeline")
    parser.add_argument(
        "--labels",
        nargs="*",
        default=None,
        help="Optional labels to filter detections.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit the number of detections shown in the console output.",
    )
    parser.add_argument(
        "--use-yolo",
        action="store_true",
        help="Switch the container to the YOLO-backed provider (requires vision deps).",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    container = ApplicationContainer()
    container.logging()
    settings = container.config()

    if args.use_yolo:
        use_yolo_provider(container)

    logger = container.logger()
    logger.info(
        "app.started",
        model_path=settings.model_path,
        device=settings.device,
    )

    with container.enter_scope("run"):
        use_case = container.vision_inference_use_case()
        request = VisionInferenceRequest(
            selected_labels=args.labels,
            limit=args.limit,
        )
        response = use_case.execute(request)

    for detection in response.detections:
        bbox = detection.bounding_box.as_tuple()
        print(
            f"label={detection.label} conf={detection.confidence:.2f} "
            f"bbox={bbox} center={detection.center}",
        )

    logger.info("app.finished", total_detections=response.total)
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
