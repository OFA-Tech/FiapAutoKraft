from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class VisionSettings:
    model_path: str
    camera_index: int
    frame_width: int
    frame_height: int
    target_fps: float
    inference_interval: int
    confidence_threshold: float
    digital_zoom: float = 1.0
    device: str | None = None
    selected_labels: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.frame_width <= 0 or self.frame_height <= 0:
            raise ValueError("Frame dimensions must be positive")
        if self.target_fps <= 0:
            raise ValueError("Target FPS must be positive")
        if self.inference_interval <= 0:
            raise ValueError("Inference interval must be positive")
        if not (0 < self.confidence_threshold <= 1):
            raise ValueError("Confidence threshold must be within (0, 1]")
        if self.digital_zoom <= 0:
            raise ValueError("Digital zoom must be positive")
