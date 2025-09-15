from pydantic import BaseModel, Field


class VideoDetectionRequestModel(BaseModel):
    """Request payload containing a base64 encoded video for YOLO processing."""

    video_base64: str = Field(
        ...,
        min_length=1,
        description="Base64 encoded representation of the video to analyse.",
    )
    frame_interval: int = Field(
        default=5,
        ge=1,
        description="Process one frame every N frames from the provided video stream.",
    )
    max_frames: int = Field(
        default=60,
        ge=1,
        le=1000,
        description="Maximum number of frames to process from the provided video stream.",
    )
