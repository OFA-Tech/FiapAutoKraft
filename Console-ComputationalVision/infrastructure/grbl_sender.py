from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass

import serial
from serial.tools import list_ports

from domain.motion.gcode_sender import CommandAck, GcodeSender
from domain.motion.position import Feedrate, Position


logger = logging.getLogger(__name__)


@dataclass
class SerialAck:
    ok: bool
    message: str
    responses: tuple[str, ...] = ()


class SerialGcodeSender(GcodeSender):
    def __init__(self) -> None:
        self._serial: serial.Serial | None = None
        self._port: str | None = None
        self._baud_rate = 115200
        self._timeout = 1.0
        self._coordinates: list[dict[str, float]] = []
        self._event_hook: callable | None = None

    # Infrastructure utilities -------------------------------------------------
    def set_event_hook(self, hook: callable | None) -> None:
        self._event_hook = hook

    def _emit_event(self, name: str, **payload) -> None:
        if not self._event_hook:
            return
        info = {
            "timestamp": time.monotonic(),
            "thread": threading.current_thread().name,
            "port": self._port,
        }
        if self._serial is not None:
            info["ser_id"] = id(self._serial)
        info.update(payload)
        try:
            self._event_hook(name, info)
        except Exception:
            logger.exception("Failed to emit instrumentation event %s", name)

    # GcodeSender API ----------------------------------------------------------
    def connect(self, port: str, baudrate: int) -> None:
        self.disconnect()
        try:
            self._serial = serial.Serial(port, baudrate, timeout=self._timeout)
        except serial.SerialException as exc:  # pragma: no cover - requires hardware
            logger.error("Error connecting to %s: %s", port, exc)
            self._serial = None
            raise
        self._port = port
        self._baud_rate = baudrate
        logger.info("Connected to %s at %s baud", port, baudrate)

    def disconnect(self) -> None:
        if self._serial and self._serial.is_open:
            self._serial.close()
            logger.info("Serial port closed")
        self._serial = None
        self._port = None

    def list_serial_ports(self):
        ports = []
        for port in list_ports.comports():
            ports.append(
                {
                    "device": port.device,
                    "name": port.name,
                    "description": port.description,
                    "hwid": port.hwid,
                    "manufacturer": port.manufacturer,
                    "product": port.product,
                    "serial_number": port.serial_number,
                }
            )
        return ports

    def send_raw(self, command: str, *, wait_for_ok: bool = True) -> CommandAck:
        responses = self._send_command(command, wait_for_ok=wait_for_ok)
        message = "ok" if wait_for_ok else "sent"
        return SerialAck(ok=True, message=message, responses=tuple(responses))

    def send_coordinates(self, position: Position, feedrate: Feedrate) -> CommandAck:
        if not self.is_connected():
            raise RuntimeError("Serial port not connected")
        x, y, z = position.x, position.y, position.z
        sum_x, sum_y, sum_z = self._sum_traces()
        if (
            sum_x + x > 5
            or sum_x + x < -5
            or sum_y + y > 5
            or sum_y + y < -5
            or sum_z + z > 4
            or sum_z + z < -4
        ):
            logger.warning("Movement exceeds range limit. Centering core instead.")
            self.home(feedrate)
            return SerialAck(ok=False, message="Range exceeded")

        commands = [
            "G21",
            "G91",
            f"F{feedrate.value}",
            f"G1 X{x:.3f} Y{y:.3f} Z{z:.3f}",
            "G90",
            "M2",
        ]
        responses: list[str] = []
        for command in commands:
            responses.extend(self._send_command(command))
        self._trace_coordinates(x, y, z)
        return SerialAck(ok=True, message="ok", responses=tuple(responses))

    def home(self, feedrate: Feedrate) -> CommandAck:
        if not self.is_connected():
            raise RuntimeError("Serial port not connected")
        if not self._coordinates:
            return SerialAck(ok=True, message="Already centered")
        sum_x, sum_y, sum_z = self._sum_traces()
        response = self.send_coordinates(
            Position(x=-sum_x, y=-sum_y, z=-sum_z),
            feedrate,
        )
        self._coordinates.clear()
        return response

    def current_position(self) -> Position | None:
        if not self.is_connected():
            return None
        sum_x, sum_y, sum_z = self._sum_traces()
        return Position(x=sum_x, y=sum_y, z=sum_z)

    def is_connected(self) -> bool:
        return bool(self._serial and self._serial.is_open)

    # Internal helpers ---------------------------------------------------------
    def _send_command(self, command: str, wait_for_ok: bool = True):
        if not self._serial or not self._serial.is_open:
            raise RuntimeError("Serial port not connected")
        command = command.rstrip("\r\n") + "\r\n"
        encoded = command.encode("utf-8")
        self._emit_event("write_start", command=command.strip(), byte_len=len(encoded))
        self._serial.write(encoded)
        self._serial.flush()
        self._emit_event("write_end", command=command.strip(), byte_len=len(encoded))
        if not wait_for_ok:
            return []
        return self._read_until_ok()

    def _read_until_ok(self, timeout_s: float = 5.0):
        assert self._serial is not None
        lines: list[str] = []
        deadline = time.monotonic() + timeout_s
        first_byte = False
        while time.monotonic() < deadline:
            raw = self._serial.readline()
            if not raw:
                continue
            decoded = raw.decode("utf-8", errors="replace").strip()
            if not decoded:
                continue
            if not first_byte:
                first_byte = True
                self._emit_event("first_byte_in", line=decoded)
            lines.append(decoded)
            if decoded == "ok" or decoded.startswith("error:"):
                self._emit_event("ok_parsed", line=decoded, lines=len(lines))
                break
        return lines

    def _trace_coordinates(self, x: float, y: float, z: float) -> None:
        self._coordinates.append({
            "x": x,
            "y": y,
            "z": z,
            "timestamp": time.monotonic(),
        })

    def _sum_traces(self) -> tuple[float, float, float]:
        sorted_coords = sorted(self._coordinates, key=lambda c: c["timestamp"])
        sum_x = sum(c["x"] for c in sorted_coords)
        sum_y = sum(c["y"] for c in sorted_coords)
        sum_z = sum(c["z"] for c in sorted_coords)
        return sum_x, sum_y, sum_z
