from pydantic import BaseModel, Field

from Domain.Models.Vision.FrameDetectionsModel import FrameDetectionsModel


class VideoDetectionResponseModel(BaseModel):
    """Response payload for object detection executed over a video."""

    model_version: str = Field(..., description="Identifier for the YOLO model that generated the detections.")
    frame_count: int = Field(..., ge=0, description="Total number of frames detected in the original video stream.")
    processed_frames: int = Field(..., ge=0, description="Number of frames that were actually processed.")
    frame_interval: int = Field(..., ge=1, description="Interval, in frames, used when sampling the video.")
    inference_time_ms: float = Field(..., ge=0.0, description="Accumulated inference time across processed frames in milliseconds.")
    frames: list[FrameDetectionsModel] = Field(default_factory=list, description="Detections grouped by processed frame.")
