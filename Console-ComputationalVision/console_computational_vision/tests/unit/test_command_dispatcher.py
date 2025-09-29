from __future__ import annotations

import logging
import time

from ...application.send_coordinates import CommandDispatcher, CommandRequest
from ...domain.motion.gcode_sender import CommandAck, GcodeSender
from ...domain.motion.position import Feedrate, Position
from ...shared.bus import EventBus


class FakeAck:
    def __init__(self, ok: bool = True, message: str = "ok") -> None:
        self.ok = ok
        self.message = message
        self.responses: tuple[str, ...] = ("ok",)


class FakeSender(GcodeSender):
    def __init__(self) -> None:
        self.commands: list[str] = []
        self.connected = True

    def connect(self, port: str, baudrate: int) -> None:
        self.connected = True

    def disconnect(self) -> None:
        self.connected = False

    def list_serial_ports(self):
        return []

    def send_raw(self, command: str, *, wait_for_ok: bool = True) -> CommandAck:
        self.commands.append(command)
        return FakeAck()

    def send_coordinates(self, position: Position, feedrate: Feedrate) -> CommandAck:
        self.commands.append(f"MOVE {position.x} {position.y} {position.z}")
        time.sleep(0.05)
        return FakeAck()

    def home(self, feedrate: Feedrate) -> CommandAck:
        self.commands.append("HOME")
        return FakeAck()

    def current_position(self):
        return Position(0.0, 0.0, 0.0)

    def is_connected(self) -> bool:
        return self.connected


def test_command_dispatcher_executes_request() -> None:
    sender = FakeSender()
    bus: EventBus[str] = EventBus()
    dispatcher = CommandDispatcher(sender, bus, logging.getLogger("test"))

    dispatcher.dispatch(
        CommandRequest(
            name="Move",
            execute=lambda: sender.send_coordinates(Position(1, 2, 3), Feedrate(200)),
            status_text="Moving",
            refresh_position=False,
        )
    )

    timeout = time.time() + 1
    while not sender.commands and time.time() < timeout:
        time.sleep(0.01)

    assert "MOVE 1 2 3" in sender.commands
