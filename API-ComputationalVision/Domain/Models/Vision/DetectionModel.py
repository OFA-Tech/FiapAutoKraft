from pydantic import BaseModel, Field

from Domain.Models.Vision.BoundingBoxModel import BoundingBoxModel


class DetectionModel(BaseModel):
    """Represents a single object detection entry."""

    class_name: str = Field(..., description="Label predicted by the YOLO model for the detected object.")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score returned by the model.")
    bounding_box: BoundingBoxModel = Field(..., description="Bounding box enclosing the detected object.")
