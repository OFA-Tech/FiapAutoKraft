from __future__ import annotations

import threading
import time

from ..domain.events import ErrorRaised, PositionUpdated
from ..domain.motion.gcode_sender import GcodeSender
from ..shared.bus import EventBus
from .send_coordinates import CommandDispatcher

POSITION_TOPIC = "gcode.position"
ERROR_TOPIC = "errors"


class PositionPoller:
    def __init__(
        self,
        sender: GcodeSender,
        dispatcher: CommandDispatcher,
        bus: EventBus,
        logger,
        interval: float = 1.0,
    ) -> None:
        self._sender = sender
        self._dispatcher = dispatcher
        self._bus = bus
        self._logger = logger
        self._interval = interval
        self._stop = threading.Event()
        self._wakeup = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="PositionPoller")
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._wakeup.set()
        if self._thread:
            self._thread.join(timeout=2)

    def trigger(self) -> None:
        self._wakeup.set()

    def _run(self) -> None:
        next_deadline = time.monotonic()
        while not self._stop.is_set():
            timeout = max(0, next_deadline - time.monotonic())
            self._wakeup.wait(timeout=timeout)
            self._wakeup.clear()

            if self._stop.is_set():
                break
            if self._dispatcher.busy():
                next_deadline = time.monotonic() + self._interval
                continue
            if not self._sender.is_connected():
                time.sleep(0.1)
                next_deadline = time.monotonic() + self._interval
                continue
            try:
                position = self._sender.current_position()
            except Exception as exc:
                self._logger.exception("Failed to poll position", exc_info=exc)
                self._bus.publish(ERROR_TOPIC, ErrorRaised("Position poll failed", exc))
                next_deadline = time.monotonic() + self._interval
                continue

            if position is not None:
                self._bus.publish(POSITION_TOPIC, PositionUpdated(position))
            next_deadline = time.monotonic() + self._interval


class PollCurrentPositionUseCase:
    def __init__(self, poller: PositionPoller) -> None:
        self._poller = poller

    def start(self) -> None:
        self._poller.start()

    def stop(self) -> None:
        self._poller.stop()

    def trigger(self) -> None:
        self._poller.trigger()
