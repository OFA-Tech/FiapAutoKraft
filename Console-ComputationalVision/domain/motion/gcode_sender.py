from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable, Protocol

from .position import Feedrate, Position


class CommandAck(Protocol):
    ok: bool
    message: str


class GcodeSender(ABC):
    """Interface for devices capable of executing G-code commands."""

    @abstractmethod
    def connect(self, port: str, baudrate: int) -> None:
        raise NotImplementedError

    @abstractmethod
    def disconnect(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def list_serial_ports(self) -> Iterable[dict]:
        raise NotImplementedError

    @abstractmethod
    def send_raw(self, command: str, *, wait_for_ok: bool = True) -> CommandAck:
        raise NotImplementedError

    @abstractmethod
    def send_coordinates(self, position: Position, feedrate: Feedrate) -> CommandAck:
        raise NotImplementedError

    @abstractmethod
    def home(self, feedrate: Feedrate) -> CommandAck:
        raise NotImplementedError

    @abstractmethod
    def current_position(self) -> Position | None:
        raise NotImplementedError

    @abstractmethod
    def is_connected(self) -> bool:
        raise NotImplementedError
