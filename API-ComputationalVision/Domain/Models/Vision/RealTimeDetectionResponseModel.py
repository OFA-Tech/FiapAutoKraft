from typing import Optional

from pydantic import BaseModel, Field

from Domain.Models.Vision.DetectionModel import DetectionModel


class RealTimeDetectionResponseModel(BaseModel):
    """Response payload returned for live camera detections."""

    model_version: str = Field(
        ..., description="Identifier for the YOLO model that generated the detections."
    )
    frame_interval: int = Field(
        ..., ge=1, description="Interval between processed frames during live detection."
    )
    frames_processed: int = Field(
        ..., ge=0, description="Number of frames analysed from the live camera stream."
    )
    inference_time_ms: float = Field(
        ..., ge=0.0, description="Total inference time accumulated while analysing the stream."
    )
    found: bool = Field(
        ..., description="Indicates if any detection matched the requested target classes."
    )
    matched_frame_index: Optional[int] = Field(
        default=None,
        ge=0,
        description="Index of the frame where a matching detection was found, when applicable.",
    )
    detections: list[DetectionModel] = Field(
        default_factory=list,
        description="Detections matching the provided target classes. Empty if none were found.",
    )
