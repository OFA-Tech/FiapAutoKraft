from __future__ import annotations

import logging
import time

from application.poll_current_position import POSITION_TOPIC, PollCurrentPositionUseCase, PositionPoller
from application.send_coordinates import CommandDispatcher
from domain.events import PositionUpdated
from domain.motion.gcode_sender import CommandAck, GcodeSender
from domain.motion.position import Feedrate, Position
from shared.bus import EventBus


class FakeAck:
    def __init__(self, ok: bool = True) -> None:
        self.ok = ok
        self.message = "ok"
        self.responses: tuple[str, ...] = ()


class FakeSender(GcodeSender):
    def __init__(self) -> None:
        self._connected = True
        self._position = Position(0.0, 0.0, 0.0)

    def connect(self, port: str, baudrate: int) -> None:
        self._connected = True

    def disconnect(self) -> None:
        self._connected = False

    def list_serial_ports(self):
        return []

    def send_raw(self, command: str, *, wait_for_ok: bool = True) -> CommandAck:
        return FakeAck()

    def send_coordinates(self, position: Position, feedrate: Feedrate) -> CommandAck:
        self._position = Position(
            self._position.x + position.x,
            self._position.y + position.y,
            self._position.z + position.z,
        )
        return FakeAck()

    def home(self, feedrate: Feedrate) -> CommandAck:
        self._position = Position(0.0, 0.0, 0.0)
        return FakeAck()

    def current_position(self) -> Position:
        return self._position

    def is_connected(self) -> bool:
        return self._connected


def test_position_poller_publishes_updates() -> None:
    sender = FakeSender()
    bus: EventBus[PositionUpdated] = EventBus()
    dispatcher = CommandDispatcher(sender, bus, logging.getLogger("poll-test"))
    poller = PositionPoller(sender, dispatcher, bus, logging.getLogger("poller"), interval=0.05)
    use_case = PollCurrentPositionUseCase(poller)

    events: list[PositionUpdated] = []
    bus.subscribe(POSITION_TOPIC, events.append)

    use_case.start()
    time.sleep(0.2)
    use_case.stop()

    assert events, "Expected at least one position update"
