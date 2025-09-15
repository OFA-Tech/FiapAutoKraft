from pydantic import BaseModel, Field

from Domain.Models.Vision.DetectionModel import DetectionModel


class FrameDetectionsModel(BaseModel):
    """Container with detections extracted from a single frame of a video."""

    frame_index: int = Field(..., ge=0, description="Zero-based index of the processed frame in the original video.")
    detections: list[DetectionModel] = Field(default_factory=list, description="List of detections found in the frame.")
