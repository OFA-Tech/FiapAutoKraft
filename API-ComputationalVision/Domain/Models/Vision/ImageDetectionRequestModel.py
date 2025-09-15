from pydantic import BaseModel, Field


class ImageDetectionRequestModel(BaseModel):
    """Request payload containing a base64 encoded image for YOLO processing."""

    image_base64: str = Field(
        ...,
        min_length=1,
        description="Base64 encoded representation of the image to analyse.",
    )
