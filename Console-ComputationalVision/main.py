from __future__ import annotations

import logging
import sys
import tkinter as tk
from typing import Any

from application.gcode_connection import GcodeConnectionService
from application.home_machine import HomeMachineUseCase
from application.list_cameras import ListCamerasUseCase
from application.list_models import ListModelsUseCase, LoadModelLabelsUseCase
from application.poll_current_position import PollCurrentPositionUseCase, PositionPoller
from application.send_coordinates import CommandDispatcher, SendCoordinatesUseCase, GCODE_LOG_TOPIC, COMMAND_STATUS_TOPIC
from application.send_raw_command import SendRawCommandUseCase
from application.start_detection import DetectionController, StartDetectionUseCase, StopDetectionUseCase
from application.update_settings import UpdateSettingsUseCase, VisionSettingsStore
from infrastructure.config_loader import ArgConfigLoader
from infrastructure.grbl_sender import SerialGcodeSender
from infrastructure.model_store import ModelStore
from infrastructure.opencv_camera import OpenCvCameraRepository
from infrastructure.yolovX_detector import YoloDetectorFactory
from presentation.gui_app import GuiApp
from shared.bus import EventBus


def configure_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def build_app(argv: list[str] | None = None) -> GuiApp:
    configure_logging()
    loader = ArgConfigLoader()
    config = loader.parse(argv)

    event_bus: EventBus[Any] = EventBus()
    logger = logging.getLogger("console_vision")

    model_store = ModelStore(config.project_root / "models")
    camera_repo = OpenCvCameraRepository(logger.getChild("camera"))
    detector_factory = YoloDetectorFactory(logger.getChild("detector"))
    gcode_sender = SerialGcodeSender()

    dispatcher = CommandDispatcher(gcode_sender, event_bus, logger.getChild("gcode"))
    settings_store = VisionSettingsStore(config.initial_settings)
    update_settings = UpdateSettingsUseCase(settings_store)
    detection_controller = DetectionController(camera_repo, detector_factory, event_bus, logger.getChild("controller"))
    start_detection = StartDetectionUseCase(detection_controller, settings_store)
    stop_detection = StopDetectionUseCase(detection_controller)

    poller = PositionPoller(gcode_sender, dispatcher, event_bus, logger.getChild("poller"))
    poll_use_case = PollCurrentPositionUseCase(poller)

    list_models = ListModelsUseCase(model_store)
    load_labels = LoadModelLabelsUseCase(model_store)
    list_cameras = ListCamerasUseCase(camera_repo)
    send_coordinates = SendCoordinatesUseCase(dispatcher, gcode_sender)
    home_machine = HomeMachineUseCase(dispatcher, gcode_sender)
    send_raw = SendRawCommandUseCase(dispatcher, gcode_sender)
    connection = GcodeConnectionService(gcode_sender, poll_use_case)

    def instrumentation_hook(name: str, payload: dict) -> None:
        event_bus.publish("gcode.instrument", (name, payload))

    gcode_sender.set_event_hook(instrumentation_hook)

    def command_status_listener(status: str) -> None:
        if status == "refresh-position":
            poll_use_case.trigger()

    event_bus.subscribe(COMMAND_STATUS_TOPIC, command_status_listener)

    def gcode_log_listener(message: str) -> None:
        logging.getLogger("console_vision.gcode").info(message)

    event_bus.subscribe(GCODE_LOG_TOPIC, gcode_log_listener)

    poll_use_case.start()

    root = tk.Tk()
    app = GuiApp(
        root=root,
        config=config,
        event_bus=event_bus,
        settings_store=settings_store,
        update_settings=update_settings,
        start_detection=start_detection,
        stop_detection=stop_detection,
        list_models=list_models,
        load_labels=load_labels,
        list_cameras=list_cameras,
        dispatcher=dispatcher,
        send_coordinates=send_coordinates,
        home_machine=home_machine,
        send_raw=send_raw,
        connection=connection,
        poller=poll_use_case,
    )
    return app


def main(argv: list[str] | None = None) -> int:
    app = build_app(argv)
    app.run()
    return 0


if __name__ == "__main__":  # pragma: no cover - manual execution entry point
    raise SystemExit(main(sys.argv[1:]))
