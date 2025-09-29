from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from domain.settings.settings import VisionSettings
from shared.paths import resolve_project_root


@dataclass(frozen=True)
class AppConfig:
    project_root: Path
    initial_settings: VisionSettings
    window_name: str


class ArgConfigLoader:
    def __init__(self, project_root: Path | None = None) -> None:
        self._project_root = project_root or resolve_project_root(Path(__file__))

    def parse(self, argv: Sequence[str] | None = None) -> AppConfig:
        parser = argparse.ArgumentParser(description="Console Computational Vision")
        parser.add_argument("--model-path", default="models/best.pt")
        parser.add_argument("--camera-index", type=int, default=0)
        parser.add_argument("--frame-width", type=int, default=1280)
        parser.add_argument("--frame-height", type=int, default=720)
        parser.add_argument("--target-fps", type=float, default=30.0)
        parser.add_argument("--inference-interval", type=int, default=3)
        parser.add_argument("--confidence-threshold", type=float, default=0.6)
        parser.add_argument("--digital-zoom", type=float, default=1.0)
        parser.add_argument("--device", choices=("cpu", "cuda"), default=None)
        parser.add_argument("--window-name", default="YOLOv12 Detection")
        args = parser.parse_args(argv)

        settings = VisionSettings(
            model_path=str(args.model_path),
            camera_index=int(args.camera_index),
            frame_width=int(args.frame_width),
            frame_height=int(args.frame_height),
            target_fps=float(args.target_fps),
            inference_interval=int(args.inference_interval),
            confidence_threshold=float(args.confidence_threshold),
            digital_zoom=float(args.digital_zoom),
            device=args.device,
            selected_labels=(),
        )
        return AppConfig(
            project_root=self._project_root,
            initial_settings=settings,
            window_name=str(args.window_name),
        )
