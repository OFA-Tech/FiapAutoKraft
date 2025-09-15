from pydantic import BaseModel, Field


class BoundingBoxModel(BaseModel):
    """Represents the coordinates of a detected bounding box."""

    xmin: float = Field(..., description="X coordinate for the top-left corner of the box.")
    ymin: float = Field(..., description="Y coordinate for the top-left corner of the box.")
    xmax: float = Field(..., description="X coordinate for the bottom-right corner of the box.")
    ymax: float = Field(..., description="Y coordinate for the bottom-right corner of the box.")
