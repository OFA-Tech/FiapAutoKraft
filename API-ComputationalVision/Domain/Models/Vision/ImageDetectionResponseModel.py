from pydantic import BaseModel, Field

from Domain.Models.Vision.DetectionModel import DetectionModel


class ImageDetectionResponseModel(BaseModel):
    """Response payload returned for object detection on static images."""

    model_version: str = Field(..., description="Identifier for the YOLO model that generated the detections.")
    inference_time_ms: float = Field(..., ge=0.0, description="Total processing time reported by the model in milliseconds.")
    detections: list[DetectionModel] = Field(default_factory=list, description="Detections found in the provided image.")
