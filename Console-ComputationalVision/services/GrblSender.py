import logging
from typing import List, Optional

from serial.tools import list_ports
import time
import serial


logger = logging.getLogger(__name__)


class GrblSender:
    def __init__(self) -> None:
        self.port: Optional[str] = None
        self.ser: Optional[serial.Serial] = None
        self.coordinates: list[dict] = []
        self._baud_rate = 115200
        self._timeout = 1

    @staticmethod
    def list_serial_ports():
        portsList = list_ports.comports()
        result = []
        for pL in portsList:
            info = {
                "device": pL.device,
                "name": pL.name,  # short name
                "description": pL.description,  # friendly description
                "hwid": pL.hwid,  # hardware ID string
                "vid": pL.vid,  # USB vendor ID (if available)
                "pid": pL.pid,  # USB product ID (if available)
                "manufacturer": pL.manufacturer,
                "product": pL.product,
                "serial_number": pL.serial_number,
                "location": pL.location,
                "interface": pL.interface,
            }
            result.append(info)
        return result

    def connect(self, port: str, baud_rate: int = 115200, timeout: float = 1) -> bool:
        self.close_connection()
        try:
            self.ser = serial.Serial(port, baud_rate, timeout=timeout)
        except serial.SerialException as exc:
            logger.error("Error connecting to %s: %s", port, exc)
            self.ser = None
            return False

        self.port = port
        self._baud_rate = baud_rate
        self._timeout = timeout
        logger.info("Connected to %s at %s baud.", port, baud_rate)
        return True

    def close_connection(self) -> None:
        if self.ser and self.ser.is_open:
            self.ser.close()
            logger.info("Serial port closed.")
        self.ser = None
        self.port = None

    def send_coordinates(self, x: float, y: float, z: float = 0, feedrate: float = 200):
        if not self.ser or not self.ser.is_open:
            raise RuntimeError("Port not open. Call connect().")
        sum_x, sum_y, sum_z = self.sum_traces()
        if z is None:
            z = 0
        if (sum_x + x > 5
                or sum_x + x < -5
                or sum_y + y > 5
                or sum_y + y < -5
                or sum_z + z > 4
                or sum_z + z < -4):
            logger.warning("Movement exceeds range limit. Centering core instead.")
            self.center_core()
            return
        commands: list = ["G21", "G91", f"F{feedrate}", f"G1 X{x:.3f} Y{y:.3f} Z{z:.3f}", "G90", "M2"]
        logger.info("Sending coordinates X:%.3f Y:%.3f Z:%.3f", x, y, z)
        for command in commands:
            self.send_command(command)
        self.trace_coordinates(x, y, z)

#region Helpers
    def send_command(self, command: str, wait_for_ok: bool = True) -> List[str]:
        if not self.ser or not self.ser.is_open:
            raise RuntimeError("Port not open. Call connect().")
        if not command.endswith("\n"):
            command += "\n"
        self.ser.write(command.encode("utf-8"))
        if wait_for_ok:
            return self.read_until_ok()
        return []

    def trace_coordinates(self, x: float, y: float, z: float = None):
        self.coordinates.append({
            "x": x,
            "y": y,
            "z": z,
            "timestamp": time.time()
        })

    def clear_trace(self):
        self.coordinates = []

    def sum_traces(self) -> tuple:
        sorted_coords = sorted(self.coordinates, key=lambda coord: coord['timestamp'])
        sum_x = sum(c['x'] for c in sorted_coords)
        sum_y = sum(c['y'] for c in sorted_coords)
        sum_z = sum(c['z'] for c in sorted_coords if c['z'] is not None)
        return sum_x, sum_y, sum_z

    def center_core(self):
        if not self.ser or not self.ser.is_open:
            raise RuntimeError("Port not open. Call connect().")
        # Reset coordinates to center (based on the trace)
        if not self.coordinates:
            logger.info("Core already centered.")
            return
        sum_x, sum_y, sum_z = self.sum_traces()
        reverse_x = -1 * sum_x
        reverse_y = -1 * sum_y
        reverse_z = -1 * sum_z

        self.send_coordinates(reverse_x, reverse_y, reverse_z)
        self.clear_trace()

    def read_until_ok(self, timeout_s: float = 5.0) -> List[str]:
        if not self.ser or not self.ser.is_open:
            raise RuntimeError("Port not open. Call connect().")
        lines: List[str] = []
        end = time.time() + timeout_s
        while time.time() < end:
            raw = self.ser.readline()
            if not raw:
                continue
            s = raw.decode("utf-8", errors="replace").strip()
            if s:
                lines.append(s)
                if s == "ok" or s.startswith("error:"):
                    break
        return lines
#endregion

if __name__ == "__main__":
    sender = GrblSender()
    available_ports = sender.list_serial_ports()
    if not available_ports:
        logger.info("No serial ports available")
    else:
        first_port = available_ports[0]["device"]
        if sender.connect(first_port):
            logger.info("Connected to %s", first_port)
            input('Press enter to continue...')
            sender.send_coordinates(-3.0, -3.0)
            sender.send_coordinates(1, 1)
            sender.send_coordinates(3.5, 2.0, 4)
            sender.center_core()
            sender.close_connection()
