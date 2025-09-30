import os
import platform
os.environ["OPENCV_LOG_LEVEL"] = "SILENT"
import sys
from pathlib import Path
import math
import cv2
from serial.tools import list_ports


class Utils:
    def list_ai_models(self, models_dir: str = "models") -> list[dict]:
        project_root = Path(sys.argv[0]).resolve().parent

        models_path = Path(models_dir)
        if not models_path.is_absolute():
            models_path = project_root / models_dir

        if not models_path.exists() or not models_path.is_dir():
            return []

        exts = {".pt", ".pth", ".onnx"}
        out: list[dict] = []
        for f in sorted(p for p in models_path.iterdir() if p.is_file() and p.suffix.lower() in exts):
            try:
                stat = f.stat()
            except OSError:
                continue

            rel_path = f.relative_to(project_root) if f.is_relative_to(project_root) else f.name
            size_bytes = stat.st_size
            out.append({
                "file_name": f.name,
                "file_relative_path": str(rel_path),
                "file_full_path": str(f.resolve()),
                "size_bytes": size_bytes,
                "human_readable_size": self.human_readable_size(size_bytes),
                "modified_ts": stat.st_mtime,
                "created_ts": stat.st_ctime,
                "ext": f.suffix.lower(),
            })
        return out

    @staticmethod
    def list_serial_ports():
        port_list = list_ports.comports()
        result = []
        for port in port_list:
            info = {
                "device": port.device,
                "name": port.name,  # short name
                "description": port.description,  # friendly description
                "hwid": port.hwid,  # hardware ID string
                "vid": port.vid,  # USB vendor ID (if available)
                "pid": port.pid,  # USB product ID (if available)
                "manufacturer": port.manufacturer,
                "product": port.product,
                "serial_number": port.serial_number,
                "location": port.location,
                "interface": port.interface,
            }
            result.append(info)
        return result

    def list_cameras(self, max_devices: int = 10) -> list[dict]:
        cameras: list[dict] = []
        for index in range(max_devices):
            try:
                cap = None
                if platform.system() == "Windows":
                    # Prefer DSHOW, fall back to MSMF. Avoids obsensor spam.
                    dshow = getattr(cv2, "CAP_DSHOW", None)
                    msmf = getattr(cv2, "CAP_MSMF", None)
                    if dshow is not None:
                        cap = cv2.VideoCapture(index, dshow)
                    elif msmf is not None:
                        cap = cv2.VideoCapture(index, msmf)
                    else:
                        cap = cv2.VideoCapture(index)
                else:
                    cap = cv2.VideoCapture(index)
                    if not cap.isOpened():
                        cap.release()
                        v4l2_backend = getattr(cv2, "CAP_V4L2", None)
                        if v4l2_backend is not None:
                            cap = cv2.VideoCapture(index, v4l2_backend)
                if not cap.isOpened():
                    cap.release()
                    continue

                width_f = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
                height_f = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)

                if width_f is None or math.isnan(width_f):
                    width_f = 0.0
                if height_f is None or math.isnan(height_f):
                    height_f = 0.0

                width = int(width_f)
                height = int(height_f)
                backend_name = ""
                get_backend = getattr(cap, "getBackendName", None)
                if callable(get_backend):
                    try:
                        backend_name = str(get_backend())
                    except Exception:
                        backend_name = ""
                cap.release()

                name = self._resolve_camera_name(index)
                descriptor_parts = [name]
                if backend_name:
                    descriptor_parts.append(backend_name)
                descriptor = " - ".join(part for part in descriptor_parts if part)
                resolution = f"{width}x{height}"
                label = f"{index}: {descriptor} ({resolution})"
                cameras.append(
                    {
                        "index": index,
                        "name": name,
                        "label": label,
                        "default_resolution": (width, height),
                    }
                )
            except Exception:
                continue
        return cameras

    @staticmethod
    def _resolve_camera_name(index: int) -> str:
        sysfs_name = Path(f"/sys/class/video4linux/video{index}/name")
        if sysfs_name.exists():
            try:
                return sysfs_name.read_text(encoding="utf-8").strip()
            except OSError:
                pass
        return f"Camera {index}"

    @staticmethod
    def human_readable_size(size_bytes: int) -> str:
        if size_bytes == 0:
            return "0B"
        size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        return f"{s} {size_name[i]}"

if __name__ == "__main__":
    utils = Utils()
    print("AI Models:")
    for model in utils.list_ai_models('../models'):
        print(model)
    print("\nSerial Ports:")
    for port in utils.list_serial_ports():
        print(port)
    print("\nCameras:")
    for cam in utils.list_cameras():
        print(cam)