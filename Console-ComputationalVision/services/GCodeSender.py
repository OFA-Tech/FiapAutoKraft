import logging
import time
from typing import Optional, Any, Dict
import asyncio
import serial

from services.Utils import Utils


class GCodeSender:
    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)
        self.serial_port: Optional[str] = None
        self.baud_rate: Optional[int] = None
        self.nano: Optional[serial.Serial] = None
        self.command_in_execution: bool = False
        self.command_timeout: int = 60
        self.coordinate_trace: list[dict] = []
        self.command_trace: list[dict] = []
        self.max_x_axis: float = 5.0
        self.min_x_axis: float = -5.0
        self.max_y_axis: float = 5.0
        self.min_y_axis: float = -5.0
        self.max_z_axis: float = 4.0
        self.min_z_axis: float = 0.0

    def sum_traces(self) -> tuple:
        sorted_coords = sorted(self.coordinate_trace, key=lambda coord: coord['time_stamp'])
        sum_x = sum(c['x'] for c in sorted_coords)
        sum_y = sum(c['y'] for c in sorted_coords)
        sum_z = sum(c['z'] for c in sorted_coords if c['z'] is not None)
        return sum_x, sum_y, sum_z

    def connect_nano(self) -> bool:
        self.close_connection()
        try:
            self.nano = serial.Serial(self.serial_port, self.baud_rate, timeout=1)
            time.sleep(2)
            self.nano.reset_input_buffer()
        except serial.SerialException as exc:
            self.logger.error(f"Error connecting to {self.serial_port}: {exc}")
            self.nano = None
            return False

        self.logger.info(f"Connected to {self.serial_port} at {self.baud_rate} baud.")
        return True

    def close_connection(self) -> bool:
        if self.nano is not None:
            if self.nano.is_open:
                self.nano.close()
            self.nano = None
            self.logger.info("Connection closed.")
            return True
        return False

    async def read_response_until_ok(self) -> list[str]:
        if not self._nano_connected():
            raise RuntimeError("Port not open. Call connect().")
        responses: list[str] = []
        deadline = time.monotonic() + self.command_timeout
        while time.monotonic() < deadline:
            raw = await asyncio.to_thread(self.nano.readline)
            if not raw:
                continue
            line = raw.decode("utf-8", errors="replace").strip()
            if line:
                responses.append(line)
                if line == "ok" or line.startswith("error:"):
                    break
        return responses

    async def send_command(self, command: str) -> bool:
        if not self._nano_connected():
            raise RuntimeError("Port not open. Call connect().")
        encoded_command = self._normalize_command(command).encode("utf-8")
        start_waiting = time.monotonic()
        while self.command_in_execution:
            await asyncio.sleep(0.1)
        end_waiting = time.monotonic()
        command_trace: Dict[str, Any] = {
            "command": command,
            "data": encoded_command,
            "waited_for": end_waiting - start_waiting,
            "start_request": time.time(),
        }
        self.command_in_execution = True
        self.nano.write(encoded_command)
        responses = await self.read_response_until_ok()
        self.nano.flush()
        self.command_in_execution = False
        command_trace["end_request"] = time.monotonic()
        command_trace["responses"] = responses
        self.command_trace.append(command_trace)
        if not any(command_trace["responses"]):
            self.logger.warning("No responses received.")
            return False
        self.logger.info(f"Got responses: {command_trace['responses']}")
        return True

    async def send_coordinates(self, x: int, y: int, z: int=0, feed_rate: int=200):
        current_x, current_y, current_z = self.sum_traces()
        if current_x + x > self.max_x_axis or current_x + x < self.min_x_axis:
            self.logger.warning(f"Coordinates x:{current_x + x} out of range. Setting to max range instead")
            x = (self.max_x_axis - current_x) if current_x + x > self.max_x_axis else (self.min_x_axis - current_x)
        if current_y + y > self.max_y_axis or current_y + y < self.min_y_axis:
            self.logger.warning(f"Coordinates y:{current_y + y} out of range. Setting to max range instead")
            y = (self.max_y_axis - current_y) if current_y + y > self.max_y_axis else (self.min_y_axis - current_y)
        if current_z + z > self.max_z_axis or current_z + z < self.min_z_axis:
            self.logger.warning(f"Coordinates z:{current_z + z} out of range. Setting to max range instead")
            z = (self.max_z_axis - current_z) if current_z + z > self.max_z_axis else (self.min_z_axis - current_z)
        commands: list[str] = [
            "G21",
            "G91",
            f"F{feed_rate}",
            f"G1 X{x:.3f} Y{y:.3f} Z{z:.3f}",
            "G90",
            "M2",
        ]
        self.logger.info(f"Sending coordinates X:{x:.3f} Y:{y:.3f} Z:{z:.3f}")
        self.coordinate_trace.append({
            "x": x,
            "y": y,
            "z": z,
            "commands": commands,
            "time_stamp": time.monotonic()
        })
        for command in commands:
            await self.send_command(command)

    async def center_core(self, feed_rate: int=200):
        if not any(self.coordinate_trace):
            self.logger.warning("Core is already centered")
            return

        sum_x, sum_y, sum_z = self.sum_traces()
        await self.send_coordinates(-sum_x, -sum_y, -sum_z, feed_rate)
        self.logger.info("Sent coordinates to center core.")
        self.coordinate_trace.clear()

    async def set_specific_coordinates(self, x: float, y: float, z: float=0, feed_rate: int=200):
        sum_x, sum_y, sum_z = self.sum_traces()
        target_x = x - sum_x
        target_y = y - sum_y
        target_z = z - sum_z
        await self.send_coordinates(target_x, target_y, target_z, feed_rate)
        self.logger.info(f"Sent coordinates to set core to X:{x} Y:{y} Z:{z}")

    @staticmethod
    def _normalize_command(command: str) -> str:
        command = command.replace("\r", "").replace("\n", "").strip()
        return f'{command}\n'

    def _nano_connected(self) -> bool:
        return bool(self.nano and self.nano.is_open)

if __name__ == "__main__":
    async def main():
        utils = Utils()
        gcode = GCodeSender()
        available_ports = utils.list_serial_ports()
        if available_ports:
            gcode.serial_port = available_ports[0]["device"]
            gcode.baud_rate = 115200
            if gcode.connect_nano():
                try:
                    await gcode.send_coordinates(3, 2, 4)
                    await gcode.center_core()
                    await gcode.send_coordinates(-3, -2, 4)
                    await gcode.center_core()
                finally:
                    gcode.close_connection()

    asyncio.run(main())

