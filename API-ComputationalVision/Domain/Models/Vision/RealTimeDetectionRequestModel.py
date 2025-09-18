from typing import Optional

from pydantic import BaseModel, Field


class RealTimeDetectionRequestModel(BaseModel):
    """Request payload for executing detections from a live camera feed."""

    camera_index: int = Field(
        default=0,
        ge=0,
        description="Index of the camera device accessible by OpenCV (default webcam is 0).",
    )
    frame_interval: int = Field(
        default=5,
        ge=1,
        le=1000,
        description="Process one frame every N frames captured from the live stream.",
    )
    max_frames: int = Field(
        default=300,
        ge=1,
        le=10000,
        description="Maximum number of frames to analyse from the live stream before stopping.",
    )
    min_confidence: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Minimum confidence required for a detection to be considered a match.",
    )
    timeout_seconds: Optional[float] = Field(
        default=15.0,
        ge=0.0,
        description="Optional timeout for the live detection session in seconds. Use null to disable.",
    )
    target_classes: Optional[list[str]] = Field(
        default=None,
        min_length=1,
        description=(
            "List of class labels to search for during live detection. "
            "When omitted any detected object will be returned."
        ),
    )
