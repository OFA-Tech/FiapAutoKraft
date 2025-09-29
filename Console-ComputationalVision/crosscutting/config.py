"""Configuration objects and factories for the application."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """Application configuration loaded from environment variables or .env files."""

    model_path: str = Field(default="models/best.pt", description="Path to the YOLO model file.")
    camera_index: int = Field(default=0, description="Index of the camera device to open.")
    frame_width: int = Field(default=1280, description="Width of captured frames in pixels.")
    frame_height: int = Field(default=720, description="Height of captured frames in pixels.")
    target_fps: float = Field(default=30.0, description="Target capture FPS hint for the camera driver.")
    inference_interval: int = Field(default=3, description="Number of frames to skip between inferences.")
    confidence_threshold: float = Field(default=0.60, description="Minimum confidence to accept a detection.")
    digital_zoom: float = Field(default=1.0, description="Digital zoom factor applied to previews.")
    device: str | None = Field(default=None, description="Explicit inference device, e.g. 'cpu' or 'cuda'.")
    log_level: str = Field(default="INFO", description="Global logging level.")

    model_config = SettingsConfigDict(env_file=".env", env_prefix="CCV_", extra="ignore")


__all__ = ["AppSettings"]
