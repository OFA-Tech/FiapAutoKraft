from typing import List

from serial.tools import list_ports
import time
import serial

class GrblSender:
    def __init__(self):
        self.port = self.select_serial_port()
        self.ser = self.connect(self.port)
        self.coordinates = []

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

    def select_serial_port(self):
        ports = self.list_serial_ports()
        if not ports:
            print("No serial ports found.")
            return None

        print("Available serial ports:")
        for idx, p in enumerate(ports, 1):
            print("-" * 40)
            print(f"[{idx}] {p['device']} - {p['description']}")
            print(f"    Manufacturer: {p['manufacturer']}")
            print(f"    Serial:       {p['serial_number']}")
            print(f"    HWID:         {p['hwid']}")

        while True:
            try:
                choice = int(input("Select port number: "))
                if 1 <= choice <= len(ports):
                    return ports[choice - 1]["device"]
                else:
                    print(f"Invalid choice. Enter a number between 1 and {len(ports)}.")
            except ValueError:
                print("Please enter a valid number.")

    @staticmethod
    def connect(port, baudRate=115200, timeout=1):
        try:
            ser = serial.Serial(port, baudRate, timeout=timeout)
            print(f"Connected to {port} at {baudRate} baud.")
            return ser
        except serial.SerialException as e:
            print(f"Error connecting to {port}: {e}")
            return None

    def close_connection(self):
        if self.ser and self.ser.is_open:
            self.ser.close()
            print("Serial port closed.")

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
            print("Movement exceeds 5 range limit. Centering core instead")
            self.center_core()
            return
        commands: list = ["G21", "G91", f"F{feedrate}"]
        if z is None:
            commands.append(f"G1 X{x:.3f} Y{y:.3f}")
        else:
            commands.append(f"G1 X{x:.3f} Y{y:.3f} Z{z:.3f}")
        commands.append("G90")
        commands.append("M2")
        print(f"Sending appending coordinates:  X => {x:.3f}, Y => {y:.3f}, Z => {z:.3f}")
        for command in commands:
            self.send_command(command)
        self.trace_coordinates(x, y, z)

#region Helpers
    def send_command(self, command):
        if not self.ser or not self.ser.is_open:
            raise RuntimeError("Port not open. Call connect().")
        if not command.endswith("\n"):
            command += "\n"
        self.ser.write(command.encode("utf-8"))
        self.read_until_ok()

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
            print("core already centered")
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
    print(f'Selected port: {sender.port}')
    print(f'Serial object: {sender.ser.is_open}')
    input('Press enter to continue...')
    sender.send_coordinates(-3.0, -3.0)
    sender.send_coordinates(1,1)
    sender.send_coordinates(3.5,2.0, 4)
    sender.center_core()
    sender.close_connection()
