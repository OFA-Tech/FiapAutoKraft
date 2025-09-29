from __future__ import annotations

from domain.motion.gcode_sender import GcodeSender
from .poll_current_position import PollCurrentPositionUseCase


class GcodeConnectionService:
    def __init__(
        self,
        sender: GcodeSender,
        poller: PollCurrentPositionUseCase,
    ) -> None:
        self._sender = sender
        self._poller = poller

    def list_ports(self):
        return list(self._sender.list_serial_ports())

    def connect(self, port: str, baudrate: int = 115200) -> None:
        self._sender.connect(port, baudrate)
        self._poller.trigger()

    def disconnect(self) -> None:
        self._sender.disconnect()
        self._poller.trigger()

    def is_connected(self) -> bool:
        return self._sender.is_connected()
