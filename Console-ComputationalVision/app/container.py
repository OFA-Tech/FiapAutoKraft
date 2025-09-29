"""Dependency injection container wiring all application components."""

from __future__ import annotations

from dependency_injector import containers, providers

from crosscutting.config import AppSettings
from crosscutting.logging_setup import get_logger, setup_logging
from data.repositories import InMemoryDetectionProvider, InMemoryDetectionRepository, YoloDetectionProvider
from services.use_cases import VisionInferenceUseCase


class ApplicationContainer(containers.DeclarativeContainer):
    """Composition root for the Console-ComputationalVision application."""

    config = providers.Singleton(AppSettings)

    logging = providers.Singleton(lambda settings: setup_logging(settings.log_level), config)

    logger = providers.Singleton(lambda: get_logger("console_computational_vision"))

    # Infrastructure bindings -------------------------------------------------
    detection_provider = providers.Singleton(InMemoryDetectionProvider)

    yolo_detection_provider = providers.Singleton(
        lambda settings: YoloDetectionProvider(
            model_path=settings.model_path,
            camera_index=settings.camera_index,
            frame_width=settings.frame_width,
            frame_height=settings.frame_height,
            target_fps=settings.target_fps,
            inference_interval=settings.inference_interval,
            confidence_threshold=settings.confidence_threshold,
            digital_zoom=settings.digital_zoom,
            device=settings.device,
        ),
        config,
    )

    detection_repository = providers.Singleton(
        InMemoryDetectionRepository,
        scope="run",
    )

    # Application services ----------------------------------------------------
    vision_inference_use_case = providers.Factory(
        VisionInferenceUseCase,
        detection_provider=detection_provider,
        detection_repository=detection_repository,
        logger=logger,
    )


def use_yolo_provider(container: ApplicationContainer) -> None:
    """Override the default provider with the YOLO-backed implementation."""

    container.detection_provider.override(container.yolo_detection_provider)


__all__ = ["ApplicationContainer", "use_yolo_provider"]
