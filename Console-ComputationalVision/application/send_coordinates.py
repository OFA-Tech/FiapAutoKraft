from __future__ import annotations

import queue
import threading
from dataclasses import dataclass
from typing import Callable

from domain.events import ErrorRaised
from domain.motion.gcode_sender import GcodeSender
from domain.motion.position import Feedrate, Position
from shared.bus import EventBus

COMMAND_STATUS_TOPIC = "gcode.command.status"
COMMAND_RESULT_TOPIC = "gcode.command.result"
GCODE_LOG_TOPIC = "gcode.log"
ERROR_TOPIC = "errors"


@dataclass
class CommandRequest:
    name: str
    execute: Callable[[], object]
    status_text: str
    refresh_position: bool = False


class CommandDispatcher:
    def __init__(self, sender: GcodeSender, bus: EventBus, logger) -> None:
        self._sender = sender
        self._bus = bus
        self._logger = logger
        self._queue: "queue.Queue[CommandRequest | None]" = queue.Queue()
        self._stop = threading.Event()
        self._worker: threading.Thread | None = None
        self._inflight = threading.Event()

    def busy(self) -> bool:
        return self._inflight.is_set()

    def start(self) -> None:
        if self._worker and self._worker.is_alive():
            return
        self._stop.clear()
        self._worker = threading.Thread(target=self._run, name="GcodeDispatcher", daemon=True)
        self._worker.start()

    def stop(self) -> None:
        self._stop.set()
        self._queue.put(None)  # type: ignore[arg-type]
        if self._worker:
            self._worker.join(timeout=3)

    def dispatch(self, request: CommandRequest) -> None:
        self.start()
        self._queue.put(request)

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                request = self._queue.get(timeout=0.1)
            except queue.Empty:
                continue
            if request is None:
                continue
            self._inflight.set()
            self._bus.publish(COMMAND_STATUS_TOPIC, request.status_text)
            ack = None
            try:
                ack = request.execute()
                if not getattr(ack, "ok", True):
                    raise RuntimeError(getattr(ack, "message", "Command failed"))
            except Exception as exc:
                self._logger.exception("Command %s failed", request.name, exc_info=exc)
                self._bus.publish(ERROR_TOPIC, ErrorRaised(f"{request.name} failed", exc))
            finally:
                self._inflight.clear()
                self._bus.publish(COMMAND_STATUS_TOPIC, "Idle")
                if ack is not None:
                    self._bus.publish(COMMAND_RESULT_TOPIC, ack)
                    responses = getattr(ack, "responses", ()) or ()
                    for line in responses:
                        self._bus.publish(GCODE_LOG_TOPIC, f"<< {line}")
                if request.refresh_position:
                    self._bus.publish(COMMAND_STATUS_TOPIC, "refresh-position")


class SendCoordinatesUseCase:
    def __init__(self, dispatcher: CommandDispatcher, sender: GcodeSender) -> None:
        self._dispatcher = dispatcher
        self._sender = sender

    def execute(self, position: Position, feedrate: Feedrate) -> None:
        def _run():
            return self._sender.send_coordinates(position, feedrate)

        self._dispatcher.dispatch(
            CommandRequest(
                name="Move",
                execute=_run,
                status_text="Moving…",
                refresh_position=True,
            )
        )
