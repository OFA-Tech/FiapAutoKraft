"""Simple dependency container with explicit lifetimes."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Callable, Iterator

from crosscutting.config import AppSettings, load_settings
from crosscutting.logging_setup import get_logger, setup_logging
from data.repositories import (
    DetectionProvider,
    DetectionResultRepository,
    InMemoryDetectionProvider,
    InMemoryDetectionRepository,
    YoloDetectionProvider,
)
from services.use_cases import VisionInferenceUseCase


@dataclass
class _Scope:
    container: "ApplicationContainer"
    detection_repository: DetectionResultRepository

    def vision_inference_use_case(self) -> VisionInferenceUseCase:
        return VisionInferenceUseCase(
            detection_provider=self.container._resolve_detection_provider(),
            detection_repository=self.detection_repository,
            logger=self.container.logger,
        )


class ApplicationContainer:
    """Composition root exposing singleton and scoped dependencies."""

    def __init__(self) -> None:
        self._settings: AppSettings | None = None
        self._logger = None
        self._detection_provider_factory: Callable[[], DetectionProvider] = InMemoryDetectionProvider
        self._post_setup_ran = False

    # ------------------------------------------------------------------
    # Singleton providers
    @property
    def settings(self) -> AppSettings:
        if self._settings is None:
            self._settings = load_settings()
        return self._settings

    @property
    def logger(self):
        if self._logger is None:
            self._logger = get_logger("console_computational_vision")
        return self._logger

    def ensure_configured(self) -> None:
        """Configure logging exactly once."""

        if not self._post_setup_ran:
            setup_logging(self.settings.log_level)
            self._post_setup_ran = True

    # ------------------------------------------------------------------
    # Scoped providers
    @contextmanager
    def enter_scope(self, name: str) -> Iterator[_Scope]:  # noqa: D401 - simple context manager
        """Create a new logical scope (e.g. per run)."""

        if name != "run":
            raise ValueError(f"Unknown scope name: {name}")
        repository = InMemoryDetectionRepository()
        try:
            yield _Scope(self, repository)
        finally:
            repository.clear()

    # ------------------------------------------------------------------
    # Provider overrides
    def use_yolo_backend(self) -> None:
        settings = self.settings
        def factory() -> DetectionProvider:
            return YoloDetectionProvider(
                model_path=settings.model_path,
                camera_index=settings.camera_index,
                frame_width=settings.frame_width,
                frame_height=settings.frame_height,
                target_fps=settings.target_fps,
                inference_interval=settings.inference_interval,
                confidence_threshold=settings.confidence_threshold,
                digital_zoom=settings.digital_zoom,
                device=settings.device,
            )
        self._detection_provider_factory = factory

    def set_detection_provider(self, factory: Callable[[], DetectionProvider]) -> None:
        self._detection_provider_factory = factory

    # ------------------------------------------------------------------
    # Internal helpers
    def _resolve_detection_provider(self) -> DetectionProvider:
        provider = self._detection_provider_factory()
        return provider


__all__ = ["ApplicationContainer"]
