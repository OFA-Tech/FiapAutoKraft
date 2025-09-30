"""Tkinter MainPage integrating GUI widgets with backend services."""

from __future__ import annotations

import asyncio
import threading
from types import SimpleNamespace
import contextlib
import tkinter as tk
from tkinter import messagebox, ttk
import cv2

from gui.widgets.DropdownInput import DropdownInput
from gui.widgets.SelectManyInput import SelectManyInput
from gui.widgets.TextInput import TextInput
from gui.widgets.ActionButton import ActionButton
from gui.widgets.LogScreen import LogScreen
from gui.widgets.CameraPreview import CameraPreview
from gui.widgets.ValueBar import ValueBar
from gui.widgets.ValueBox import ValueBox
from services.GCodeSender import GCodeSender
from services.Utils import Utils
from services.vision_service import VisionService
from services.integration_service import VisionToGCodeIntegrator


class MainPage(tk.Frame):
    """Main GUI page wired to the Utils, VisionService, and GCodeSender modules."""

    DEFAULT_FPS_OPTIONS = ["15", "30", "60"]

    def __init__(self, master):
        super().__init__(master)
        self.pack(fill="both", expand=True)

        # Services -----------------------------------------------------------
        self.utils = Utils()
        self.gcode_sender = GCodeSender()
        self.vision_service: VisionService | None = None
        self._vision_thread: threading.Thread | None = None
        self._vision_stop_event: threading.Event | None = None
        self.integration_service = VisionToGCodeIntegrator(
            self.gcode_sender,
            run_async=self._run_gcode_async,
            log_python=self._log_python,
            log_gcode=self._log_gcode,
        )

        # Runtime state ------------------------------------------------------
        self._camera_capture: cv2.VideoCapture | None = None
        self._selected_camera: str | None = None
        self._camera_lookup: dict[str, dict] = {}
        self._selected_labels: list[str] = []

        self.py_log: LogScreen | None = None
        self.gcode_log: LogScreen | None = None
        self.state_box: ValueBox | None = None
        self.x_box: ValueBox | None = None
        self.y_box: ValueBox | None = None
        self.z_box: ValueBox | None = None

        # Build UI -----------------------------------------------------------
        self._build_ui()
        self._load_initial_data()

    def _tight_pack(self, widget, *, x=6, y=3, fill="x"):
        """Override the widget's default pack spacing (widgets auto-pack themselves)."""
        try:
            widget.pack_configure(padx=x, pady=y, fill=fill, expand=(fill == "both"))
        except tk.TclError:
            pass

    # --------------------------------------------------------------------- UI
    def _build_ui(self):
        # two columns
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)

        # ===================== LEFT COLUMN =====================
        left = ttk.Frame(self)
        left.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        left.columnconfigure(0, weight=1)

        # --- Camera & AI Settings ---
        cam_ai = ttk.LabelFrame(left, text="Camera and AI Settings", padding=(6, 4))
        cam_ai.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)
        cam_ai.columnconfigure(0, weight=1)

        # Model path
        self.inp_model = DropdownInput(
            cam_ai,
            items=[],
            label_text="Model path",
            on_change=self._on_model_changed,
            info_text="Select a model for the AI to use",
            refresh_function=self._populate_models,
        )
        self._tight_pack(self.inp_model)

        # Camera
        self.dd_camera = DropdownInput(
            cam_ai,
            items=[],
            label_text="Camera",
            on_change=self._on_camera_changed,
            info_text="Select a directshow camera device",
            width=36,
            refresh_function=self._refresh_cameras
        )
        self._tight_pack(self.dd_camera)

        # Target FPS
        self.dd_fps = DropdownInput(
            cam_ai,
            items=[(fps, fps) for fps in self.DEFAULT_FPS_OPTIONS],
            label_text="Target FPS",
            on_change=lambda v: None,
            info_text="UI refresh target; preview thread adapts accordingly",
            width=12
        )
        self._tight_pack(self.dd_fps)

        # Inference interval (number)
        self.inp_interval = TextInput(
            cam_ai,
            label_text="Inference interval:",
            on_submit=lambda v: None,
            info_text="Run detection every N frames",
            input_type="number",
            width=12
        )
        self.inp_interval.set_value(3)
        self._tight_pack(self.inp_interval)

        # Confidence threshold (slider)
        self.inp_conf = ValueBar(
            cam_ai,
            min_value=0, max_value=1, default_value=0.6, decimals=2,
            label_text="Confidence threshold:",
            info_text="Minimum confidence [0..1] to draw/emit",
            orient="horizontal",
            on_change=lambda v: None,
        )
        self._tight_pack(self.inp_conf, fill="x")

        # Device
        self.dd_device = DropdownInput(
            cam_ai,
            items=[("auto", "auto"), ("cpu", "cpu"), ("cuda", "cuda")],
            label_text="Device",
            on_change=lambda v: None,
            info_text="Inference device selection",
            width=16
        )
        self._tight_pack(self.dd_device)

        # Start/Stop row (tighter padding)
        row = ttk.Frame(cam_ai)
        row.pack(fill="x", padx=6, pady=4)
        self.state_box = ValueBox(row, title="State:", value="Idle")
        self.state_box.pack_configure(side="left", padx=6, expand=True)
        self.x_box = ValueBox(row, title="Current X:", value=0)
        self.x_box.pack_configure(side="left", padx=6, expand=True)
        self.y_box = ValueBox(row, title="Current Y:", value=0)
        self.y_box.pack_configure(side="left", padx=6, expand=True)
        self.z_box = ValueBox(row, title="Current Z:", value=0)
        self.z_box.pack_configure(side="left", padx=6, expand=True)
        btn_stop = ActionButton(row, text="Stop", on_action=self._on_stop_clicked)
        btn_stop.pack_configure(side="right", padx=6, expand=True)  # put next to it
        btn_start = ActionButton(row, text="Start", on_action=self._on_start_clicked)
        btn_start.pack_configure(side="right", padx=6, expand=True)  # override the auto-pack


        # Label filters
        filters = ttk.LabelFrame(left, text="Label filters", padding=(6, 4))
        filters.grid(row=1, column=0, sticky="nsew", padx=4, pady=6)
        filters.columnconfigure(0, weight=1)

        btns = ttk.Frame(filters); btns.pack(fill="x", padx=6, pady=(4, 2))
        ttk.Button(btns, text="Select all", command=self._label_select_all).pack(side="left")
        ttk.Label(btns, text="").pack(side="left", expand=True)
        ttk.Button(btns, text="Clear", command=self._label_clear).pack(side="left")

        self.sel_labels = SelectManyInput(
            filters,
            items=[],
            label_text="",
            on_change=self._on_labels_changed,
            height=6
        )
        self._tight_pack(self.sel_labels, fill="both")

        # --- G-code Sender ---
        gcode = ttk.LabelFrame(left, text="G-code Sender", padding=(6, 4))
        gcode.grid(row=2, column=0, sticky="nsew", padx=4, pady=4)
        gcode.columnconfigure(0, weight=1)

        self.dd_serial = DropdownInput(
            gcode,
            items=[],
            label_text="Serial port",
            on_change=lambda v: None,
            info_text="Pick the serial port connected to the controller",
            width=44,
            refresh_function=self._refresh_serial_ports,
        )
        self._tight_pack(self.dd_serial)

        row2 = ttk.Frame(gcode); row2.pack(fill="x", padx=6, pady=2)
        btn_connect =ActionButton(row2, text="Connect", on_action=self._on_connect)
        btn_connect.pack_configure(side="left", padx=6, expand=True)
        btn_disconnect = ActionButton(row2, text="Disconnect", on_action=self._on_disconnect)
        btn_disconnect.pack_configure(side="left", padx=6, expand=True)

        pos = ttk.Frame(gcode); pos.pack(fill="x", padx=6, pady=4)
        self.inp_x = TextInput(pos, label_text="X:", width=6, input_type="number")
        self.inp_x.pack_configure(side="left", padx=6, expand=True)
        self.inp_y = TextInput(pos, label_text="Y:", width=6, input_type="number")
        self.inp_y.pack_configure(side="left", padx=6, expand=True)
        self.inp_z = TextInput(pos, label_text="Z:", width=6, input_type="number")
        self.inp_z.pack_configure(side="left", padx=6, expand=True)
        self.inp_feed = TextInput(pos, label_text="Feedrate:", width=8, input_type="number")
        self.inp_feed.pack_configure(side="left", padx=6, expand=True)
        send_gcode = ActionButton(pos, text="Send", on_action=self._on_send_move)
        send_gcode.pack_configure(side="left", padx=6, expand=True)
        center_core = ActionButton(pos, text="Center-It", on_action=self._on_home)
        center_core.pack_configure(side="left", padx=6, expand=True)

        line = ttk.Frame(gcode); line.pack(fill="x", padx=6, pady=(2, 6))
        self.inp_gline = TextInput(line, label_text="Raw G-Code", on_submit=self._on_send_line, width=48); self._tight_pack(self.inp_gline)
        ActionButton(line, text="Send", on_action=self._on_send_line)

        # give left sections stretch
        left.rowconfigure(3, weight=1)

        # ===================== RIGHT COLUMN =====================
        right = ttk.Frame(self)
        right.grid(row=0, column=1, sticky="nsew", padx=8, pady=8)
        right.columnconfigure(0, weight=1)
        right.rowconfigure(0, weight=1)

        # Camera Preview group
        preview_group = ttk.LabelFrame(right, text="Camera Preview", padding=(6, 4))
        preview_group.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)
        preview_group.columnconfigure(0, weight=1)
        preview_group.rowconfigure(0, weight=1)

        # Holder to center the preview
        holder = ttk.Frame(preview_group)
        holder.grid(row=0, column=0, sticky="n")  # top-center
        holder.columnconfigure(0, weight=1)

        self.preview = CameraPreview(holder, width=640, height=360, fps=30,
                                     capture=None)
        # Stop it from filling; center it
        try:
            self.preview.pack_configure(padx=0, pady=0, fill=None, expand=False)
        except tk.TclError:
            pass

        # Gcode|Python Logs group
        pylog_group = ttk.LabelFrame(right, text="G-code | Python Logs", padding=(6, 4))
        pylog_group.grid(row=1, column=0, sticky="nsew", padx=4, pady=(6, 0))
        self.py_log = LogScreen(pylog_group, logs=[], height=10, width=80)
        self.gcode_log = LogScreen(pylog_group, logs=[], height=10, width=80)

        right.rowconfigure(1, weight=1)

    # -------------------------------------------------------- Data loading
    def _load_initial_data(self) -> None:
        self._populate_models()
        try:
            asyncio.run(self._refresh_cameras())
        except RuntimeError as exc:
            # Fallback for environments that already run an event loop.
            self._log_python(f"Camera refresh failed: {exc}")
            threading.Thread(
                target=lambda: asyncio.run(self._refresh_cameras()),
                name="CameraRefreshFallback",
                daemon=True,
            ).start()
        self._refresh_serial_ports()

    def _populate_models(self) -> None:
        try:
            models = self.utils.list_ai_models("models")
        except Exception as exc:
            self._log_python(f"Failed to load models: {exc}")
            self.inp_model.set_items([])
            return

        items: list[tuple[str, str]] = []
        for model in models:
            value = model.get("file_full_path") or model.get("file_relative_path")
            if not value:
                continue
            name = model.get("file_name", value)
            size = model.get("human_readable_size")
            label = f"{name} ({size})" if size else name
            items.append((value, label))

        if not items:
            self.inp_model.set_items([])
            self.sel_labels.set_items([])
            self._selected_labels = []
            self._log_python("No AI models found in the models directory.")
            return

        self.inp_model.set_items(items)
        self._log_python(f"Loaded {len(items)} model(s).")

    async def _refresh_cameras(self):
        try:
            cameras = await asyncio.to_thread(self.utils.list_cameras)
        except Exception as exc:
            self._log_python(f"Failed to enumerate cameras: {exc}")

            def clear_ui():
                self.dd_camera.set_items([])
                self._selected_camera = None
                self._camera_lookup.clear()
                self._release_camera_capture()
                self.preview.stop()
                self.preview.set_capture(None)

            self.after(0, clear_ui)
            return

        def apply_results(cameras=cameras):
            items: list[tuple[str, str]] = []
            self._camera_lookup.clear()
            for cam in cameras:
                index = cam.get("index")
                label = cam.get("label") or str(index)
                if index is None:
                    continue
                key = str(index)
                items.append((key, label))
                self._camera_lookup[key] = cam

            if not items:
                self.dd_camera.set_items([])
                self._selected_camera = None
                self._release_camera_capture()
                self.preview.stop()
                self.preview.set_capture(None)
                self._log_python("No cameras detected.")
                return

            self.dd_camera.set_items(items)
            self._log_python(f"Detected {len(items)} camera(s).")

        self.after(0, apply_results)

    def _refresh_serial_ports(self):
        try:
            ports = self.utils.list_serial_ports()
        except Exception as exc:
            self._log_gcode(f"Failed to enumerate serial ports: {exc}")
            self.dd_serial.set_items([])
            return

        items: list[tuple[str, str]] = []
        for port in ports:
            device = port.get("device")
            if not device:
                continue
            description = port.get("description") or port.get("name") or device
            label = f"{device} ({description})" if description else device
            items.append((device, label))

        if not items:
            self.dd_serial.set_items([])
            self._log_gcode("No serial ports available.")
            return

        self.dd_serial.set_items(items)
        self._log_gcode(f"Loaded {len(items)} serial port(s).")

    # ----------------------------------------------------- Callbacks
    def _on_model_changed(self, model_path: str | None):
        if not model_path:
            self.sel_labels.set_items([])
            self._selected_labels = []
            return

        try:
            labels = VisionService.discover_model_labels(model_path)
        except Exception as exc:
            self._log_python(f"Failed to load labels for model: {exc}")
            messagebox.showerror("Model labels", f"Could not load labels: {exc}")
            return

        formatted = [(label, label) for label in labels]
        self.sel_labels.set_items(formatted)
        self._selected_labels = self.sel_labels.get_values() if hasattr(self.sel_labels, "get_values") else list(labels)
        self._log_python(f"Loaded {len(labels)} label(s) from model.")

    def _on_camera_changed(self, cam_value):
        self._selected_camera = cam_value if cam_value is not None else None

        if self._vision_thread and self._vision_thread.is_alive():
            # Vision service owns the camera when running.
            return

        self._release_camera_capture()
        if cam_value is None:
            self.preview.set_capture(None)
            return

        try:
            idx = int(cam_value)
        except (TypeError, ValueError):
            self._log_python(f"Invalid camera index selected: {cam_value}")
            return

        cap = cv2.VideoCapture(idx)
        if not cap.isOpened():
            cap.release()
            self.preview.set_capture(None)
            self._log_python(f"Unable to open camera index {idx} for preview.")
            return

        self._camera_capture = cap
        self.preview.set_capture(cap)
        self.preview.start()
        self._log_python(f"Previewing camera index {idx}.")

    def _on_start_clicked(self):
        if self._vision_thread and self._vision_thread.is_alive():
            messagebox.showinfo("Vision", "The vision service is already running.")
            return

        try:
            args = self._collect_vision_args()
        except ValueError as exc:
            messagebox.showerror("Invalid configuration", str(exc))
            return

        try:
            self.vision_service = VisionService(args)
        except Exception as exc:
            self._log_python(f"Failed to start vision service: {exc}")
            messagebox.showerror("Vision", f"Unable to start vision service: {exc}")
            self.vision_service = None
            return

        try:
            self.vision_service.select_labels(self._selected_labels or None)
        except ValueError as exc:
            messagebox.showwarning("Labels", str(exc))

        self._release_camera_capture()
        self.preview.stop()
        self.preview.set_capture(None)

        self.integration_service.reset()
        self._vision_stop_event = threading.Event()
        self._vision_thread = threading.Thread(
            target=self._run_vision_service,
            name="VisionServiceThread",
            daemon=True,
        )
        self._vision_thread.start()
        self._set_state("Running")
        self._log_python("Vision service started.")

    def _on_stop_clicked(self):
        self._stop_vision_service()
        self.preview.stop()
        if self._selected_camera is not None:
            # Restore raw preview when not running vision.
            self._on_camera_changed(self._selected_camera)
        self._set_state("Idle")
        self._log_python("Vision service stopped.")

    def _label_select_all(self):
        values = list(self.sel_labels._values_to_names.keys())
        self.sel_labels.set_values(values)

    def _label_clear(self):
        self.sel_labels.set_values([])

    def _on_labels_changed(self, values):
        self._selected_labels = list(values)
        if self.vision_service:
            try:
                self.vision_service.select_labels(values or None)
            except ValueError as exc:
                messagebox.showwarning("Labels", str(exc))
        self._log_python(f"Label filter changed: {values}")

    def _on_connect(self):
        port = self.dd_serial.get_value()
        if not port:
            messagebox.showwarning("Serial port", "Please select a serial port before connecting.")
            return

        self.gcode_sender.serial_port = port
        self.gcode_sender.baud_rate = 115200
        if self.gcode_sender.connect_nano():
            self._log_gcode(f"Connected to {port}.")
        else:
            self._log_gcode(f"Failed to connect to {port}.")

    def _on_disconnect(self):
        if self.gcode_sender.close_connection():
            self._log_gcode("Serial connection closed.")
        else:
            self._log_gcode("No open serial connection to close.")

    def _on_send_move(self):
        x = self.inp_x.get_value()
        y = self.inp_y.get_value()
        z = self.inp_z.get_value()
        f = self.inp_feed.get_value()
        if not self._ensure_gcode_ready():
            return

        x = 0.0 if x is None else float(x)
        y = 0.0 if y is None else float(y)
        z = 0.0 if z is None else float(z)
        feed = 200 if f is None else int(f)

        self._run_gcode_async(
            self.gcode_sender.send_coordinates(x, y, z, feed),
            success_message=f"Move -> X:{x} Y:{y} Z:{z} F:{feed}",
        )

    def _on_home(self):
        if not self._ensure_gcode_ready():
            return
        self._run_gcode_async(
            self.gcode_sender.center_core(),
            success_message="Center command sent.",
        )

    def _on_send_line(self, *_):
        line = self.inp_gline.get_value()
        if line:
            if not self._ensure_gcode_ready():
                return
            self._run_gcode_async(
                self.gcode_sender.send_command(line),
                success_message=f"> {line}",
            )

    # ----------------------------------------------------- Helpers
    def _collect_vision_args(self) -> SimpleNamespace:
        model_path = self.inp_model.get_value()
        if not model_path:
            raise ValueError("Please select a model path.")

        camera_value = self.dd_camera.get_value()
        if camera_value is None:
            raise ValueError("Please select a camera.")
        try:
            camera_index = int(camera_value)
        except (TypeError, ValueError) as exc:
            raise ValueError("Selected camera index is invalid.") from exc

        fps_value = self.dd_fps.get_value() or self.DEFAULT_FPS_OPTIONS[0]
        try:
            target_fps = float(fps_value)
        except (TypeError, ValueError) as exc:
            raise ValueError("Selected FPS is invalid.") from exc

        interval = self.inp_interval.get_value()
        if interval is None:
            raise ValueError("Inference interval cannot be empty.")
        inference_interval = max(1, int(interval))

        confidence = self.inp_conf.get_value()
        confidence_threshold = float(confidence)

        device_value = self.dd_device.get_value()
        device = None if device_value == "auto" else device_value

        camera_info = self._camera_lookup.get(str(camera_index), {})
        width, height = camera_info.get("default_resolution", (640, 480))
        if not width or not height:
            width, height = 640, 480

        return SimpleNamespace(
            model_path=model_path,
            camera_index=camera_index,
            frame_width=int(width),
            frame_height=int(height),
            target_fps=target_fps,
            inference_interval=inference_interval,
            confidence_threshold=confidence_threshold,
            digital_zoom=1.0,
            device=device,
            window_name="Console Computational Vision",
        )

    def _run_vision_service(self) -> None:
        assert self.vision_service is not None
        stop_event = self._vision_stop_event
        try:
            self.vision_service.run(
                frame_callback=self._on_vision_frame,
                stop_event=stop_event,
                detection_callback=self._on_vision_detections,
            )
        except Exception as exc:
            self._log_python(f"Vision service stopped with error: {exc}")
            self.after(0, lambda err=exc: messagebox.showerror("Vision", f"Vision service error: {err}"))
        finally:
            self.after(0, self._set_state, "Idle")
            self.after(0, setattr, self, "vision_service", None)
            self.after(0, self._restore_preview_after_service)
            self.integration_service.reset()
            self._vision_thread = None
            self._vision_stop_event = None

    def _stop_vision_service(self) -> None:
        stop_event = self._vision_stop_event
        if stop_event:
            stop_event.set()
        thread = self._vision_thread
        if thread and thread.is_alive():
            thread.join(timeout=5)
        self._vision_thread = None
        self._vision_stop_event = None
        self.vision_service = None
        self.integration_service.reset()

    def _on_vision_frame(self, frame):
        self.preview.display_frame(frame)

    def _on_vision_detections(self, detections: list[dict], frame_size: tuple[int, int]) -> None:
        try:
            self.integration_service.handle_detections(detections, frame_size)
        except Exception as exc:
            self._log_python(f"Integration error: {exc}")

    def _restore_preview_after_service(self) -> None:
        if self._selected_camera is None:
            return
        if self._vision_thread and self._vision_thread.is_alive():
            return
        if self._camera_capture is not None and getattr(self._camera_capture, "isOpened", lambda: False)():
            return
        self._on_camera_changed(self._selected_camera)

    def _release_camera_capture(self) -> None:
        if self._camera_capture is not None:
            with contextlib.suppress(Exception):
                if self._camera_capture.isOpened():
                    self._camera_capture.release()
        self._camera_capture = None

    def _ensure_gcode_ready(self) -> bool:
        if not self.gcode_sender.nano or not getattr(self.gcode_sender.nano, "is_open", False):
            messagebox.showwarning("G-code", "Connect to the controller before sending commands.")
            return False
        return True

    def _run_gcode_async(self, coro, *, success_message: str | None = None) -> None:
        def worker():
            try:
                asyncio.run(coro)
            except Exception as exc:
                self._log_gcode(f"G-code error: {exc}")
            else:
                if success_message:
                    self._log_gcode(success_message)
                self._update_position_boxes()

        threading.Thread(target=worker, daemon=True).start()

    def _update_position_boxes(self) -> None:
        if not self.x_box or not self.y_box or not self.z_box:
            return
        try:
            sum_x, sum_y, sum_z = self.gcode_sender.sum_traces()
        except Exception:
            return

        self.after(0, self.x_box.set_value, round(sum_x, 3))
        self.after(0, self.y_box.set_value, round(sum_y, 3))
        self.after(0, self.z_box.set_value, round(sum_z, 3))

    def _set_state(self, state: str) -> None:
        if self.state_box:
            self.state_box.set_value(state)

    def _log_python(self, message: str) -> None:
        if self.py_log:
            self.after(0, self.py_log.append_log, message)

    def _log_gcode(self, message: str) -> None:
        if self.gcode_log:
            self.after(0, self.gcode_log.append_log, message)


# --------------------------- Standalone run ---------------------------
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Console Computational Vision")
    root.geometry("1280x720")
    root.rowconfigure(0, weight=1)
    root.columnconfigure(0, weight=1)
    MainPage(root)
    root.mainloop()
