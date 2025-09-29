from __future__ import annotations

import logging
import queue
import sys
import tkinter as tk
from tkinter import messagebox, ttk

from application.gcode_connection import GcodeConnectionService
from application.home_machine import HomeMachineUseCase
from application.list_cameras import ListCamerasUseCase
from application.list_models import ListModelsUseCase, LoadModelLabelsUseCase
from application.poll_current_position import PollCurrentPositionUseCase
from application.send_coordinates import CommandDispatcher
from application.send_raw_command import SendRawCommandUseCase
from application.start_detection import (
    DETECTION_TOPIC,
    DEVICE_TOPIC,
    ERROR_TOPIC,
    StartDetectionUseCase,
    StopDetectionUseCase,
)
from application.update_settings import UpdateSettingsRequest, UpdateSettingsUseCase, VisionSettingsStore
from domain.events import DetectionProduced, DeviceStateChanged, ErrorRaised
from infrastructure.config_loader import AppConfig
from infrastructure.logging_sink import QueueStreamRedirector, TkQueueHandler
from shared.bus import EventBus
from .widgets.camera_preview import CameraPreview
from .widgets.gcode_sender_panel import GcodeSenderPanel
from .widgets.python_logs import PythonLogsWidget


class GuiApp:
    def __init__(
        self,
        root: tk.Tk,
        config: AppConfig,
        event_bus: EventBus,
        settings_store: VisionSettingsStore,
        update_settings: UpdateSettingsUseCase,
        start_detection: StartDetectionUseCase,
        stop_detection: StopDetectionUseCase,
        list_models: ListModelsUseCase,
        load_labels: LoadModelLabelsUseCase,
        list_cameras: ListCamerasUseCase,
        dispatcher: CommandDispatcher,
        send_coordinates,
        home_machine: HomeMachineUseCase,
        send_raw: SendRawCommandUseCase,
        connection: GcodeConnectionService,
        poller: PollCurrentPositionUseCase,
    ) -> None:
        self.root = root
        self.root.title(config.window_name)
        self._config = config
        self._bus = event_bus
        self._settings_store = settings_store
        self._update_settings = update_settings
        self._start_detection = start_detection
        self._stop_detection = stop_detection
        self._list_models = list_models
        self._load_labels = load_labels
        self._list_cameras = list_cameras
        self._dispatcher = dispatcher
        self._send_coordinates = send_coordinates
        self._home_machine = home_machine
        self._send_raw = send_raw
        self._connection = connection
        self._poller = poller

        self._logger = logging.getLogger(__name__)
        self._detection_running = False
        self._camera_lookup: dict[str, object] = {}

        self._detection_queue: "queue.Queue[DetectionProduced]" = queue.Queue()
        self._device_queue: "queue.Queue[DeviceStateChanged]" = queue.Queue()
        self._error_queue: "queue.Queue[ErrorRaised]" = queue.Queue()
        self._python_log_queue: "queue.Queue[str]" = queue.Queue()
        handler = TkQueueHandler(self._python_log_queue)
        handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s", "%H:%M:%S"))
        root_logger = logging.getLogger()
        for existing in list(root_logger.handlers):
            root_logger.removeHandler(existing)
        root_logger.addHandler(handler)
        root_logger.setLevel(logging.INFO)
        logging.captureWarnings(True)
        self._stdout_redirector = QueueStreamRedirector(self._python_log_queue, "STDOUT")
        self._stderr_redirector = QueueStreamRedirector(self._python_log_queue, "STDERR")
        self._original_stdout = sys.stdout
        self._original_stderr = sys.stderr
        sys.stdout = self._stdout_redirector
        sys.stderr = self._stderr_redirector

        self._build_layout()
        self._register_bus_subscriptions()
        self._schedule_python_log_update()
        self._schedule_detection_updates()
        self._schedule_device_updates()
        self._schedule_error_updates()

        self.root.protocol("WM_DELETE_WINDOW", self.shutdown)

    def _build_layout(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.columnconfigure(1, weight=3)
        self.root.rowconfigure(0, weight=1)

        self.control_frame = ttk.LabelFrame(self.root, text="Camera and AI Settings")
        self.control_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.control_frame.columnconfigure(1, weight=1)
        self.control_frame.rowconfigure(8, weight=1)

        self._build_controls()

        preview_frame = ttk.LabelFrame(self.root, text="Camera Preview")
        preview_frame.grid(row=0, column=1, sticky="nsew", padx=(0, 10), pady=10)
        preview_frame.rowconfigure(0, weight=3)
        preview_frame.rowconfigure(1, weight=2)
        preview_frame.columnconfigure(0, weight=1)

        self.preview = CameraPreview(preview_frame)
        self.preview.widget().grid(row=0, column=0, sticky="nsew")

        logs_frame = ttk.LabelFrame(preview_frame, text="Python Logs")
        logs_frame.grid(row=1, column=0, sticky="nsew", padx=6, pady=(6, 6))
        logs_frame.rowconfigure(0, weight=1)
        logs_frame.columnconfigure(0, weight=1)
        self.python_logs = PythonLogsWidget(logs_frame)
        self.python_logs.widget().grid(row=0, column=0, sticky="nsew")

        self.gcode_panel = GcodeSenderPanel(
            self.control_frame,
            self._bus,
            self._dispatcher,
            self._connection,
            self._send_coordinates,
            self._home_machine,
            self._send_raw,
            self._poller,
        )
        self.gcode_panel.frame.grid(row=7, column=0, columnspan=3, sticky="nsew", pady=(10, 0))

    def _build_controls(self) -> None:
        row = 0
        ttk.Label(self.control_frame, text="Model path").grid(row=row, column=0, sticky="w", pady=2)
        self.model_var = tk.StringVar(value=self._config.initial_settings.model_path)
        self.model_combo = ttk.Combobox(self.control_frame, textvariable=self.model_var, state="readonly")
        self.model_combo.grid(row=row, column=1, sticky="ew", pady=2)
        ttk.Button(self.control_frame, text="🔃", width=3, command=self._refresh_models).grid(row=row, column=2, padx=4)
        self.model_combo.bind("<<ComboboxSelected>>", lambda _event: self._on_model_selected())

        row += 1
        ttk.Label(self.control_frame, text="Camera").grid(row=row, column=0, sticky="w", pady=2)
        self.camera_var = tk.StringVar()
        self.camera_combo = ttk.Combobox(self.control_frame, textvariable=self.camera_var, state="readonly")
        self.camera_combo.grid(row=row, column=1, sticky="ew", pady=2)
        ttk.Button(self.control_frame, text="🔃", width=3, command=self._refresh_cameras).grid(row=row, column=2, padx=4)
        self.camera_combo.bind("<<ComboboxSelected>>", lambda _event: self._on_camera_selected())

        row += 1
        ttk.Label(self.control_frame, text="Target FPS").grid(row=row, column=0, sticky="w", pady=2)
        self.target_fps_var = tk.StringVar(value=str(int(self._config.initial_settings.target_fps)))
        self.target_fps_combo = ttk.Combobox(
            self.control_frame,
            textvariable=self.target_fps_var,
            values=("15", "30", "60"),
            state="readonly",
        )
        self.target_fps_combo.grid(row=row, column=1, sticky="ew", pady=2)

        row += 1
        ttk.Label(self.control_frame, text="Frame width").grid(row=row, column=0, sticky="w", pady=2)
        self.frame_width_var = tk.StringVar(value=str(self._config.initial_settings.frame_width))
        ttk.Entry(self.control_frame, textvariable=self.frame_width_var).grid(row=row, column=1, sticky="ew", pady=2)

        row += 1
        ttk.Label(self.control_frame, text="Frame height").grid(row=row, column=0, sticky="w", pady=2)
        self.frame_height_var = tk.StringVar(value=str(self._config.initial_settings.frame_height))
        ttk.Entry(self.control_frame, textvariable=self.frame_height_var).grid(row=row, column=1, sticky="ew", pady=2)

        row += 1
        ttk.Label(self.control_frame, text="Inference interval").grid(row=row, column=0, sticky="w", pady=2)
        self.inference_var = tk.StringVar(value=str(self._config.initial_settings.inference_interval))
        ttk.Entry(self.control_frame, textvariable=self.inference_var).grid(row=row, column=1, sticky="ew", pady=2)

        row += 1
        ttk.Label(self.control_frame, text="Confidence threshold").grid(row=row, column=0, sticky="w", pady=2)
        self.confidence_var = tk.StringVar(value=str(self._config.initial_settings.confidence_threshold))
        ttk.Entry(self.control_frame, textvariable=self.confidence_var).grid(row=row, column=1, sticky="ew", pady=2)

        row += 1
        ttk.Label(self.control_frame, text="Digital zoom").grid(row=row, column=0, sticky="w", pady=2)
        self.zoom_var = tk.StringVar(value=f"{self._config.initial_settings.digital_zoom:.1f}")
        ttk.Spinbox(self.control_frame, textvariable=self.zoom_var, from_=1.0, to=2.5, increment=0.1, format="%.1f").grid(row=row, column=1, sticky="ew", pady=2)

        row += 1
        ttk.Label(self.control_frame, text="Device").grid(row=row, column=0, sticky="w", pady=2)
        self.device_var = tk.StringVar(value=self._config.initial_settings.device or "auto")
        self.device_combo = ttk.Combobox(self.control_frame, textvariable=self.device_var, values=("auto", "cpu", "cuda"), state="readonly")
        self.device_combo.grid(row=row, column=1, sticky="ew", pady=2)

        row += 1
        button_bar = ttk.Frame(self.control_frame)
        button_bar.grid(row=row, column=0, columnspan=3, pady=(10, 0), sticky="ew")
        button_bar.columnconfigure(0, weight=1)
        button_bar.columnconfigure(1, weight=1)
        self.start_button = ttk.Button(button_bar, text="Start", command=self.start_detection)
        self.start_button.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        self.stop_button = ttk.Button(button_bar, text="Stop", command=self.stop_detection, state="disabled")
        self.stop_button.grid(row=0, column=1, sticky="ew")

        row += 1
        status_frame = ttk.Frame(self.control_frame)
        status_frame.grid(row=row, column=0, columnspan=3, sticky="w", pady=(8, 0))
        ttk.Label(status_frame, text="State:").grid(row=0, column=0, sticky="w")
        self.status_var = tk.StringVar(value="Idle")
        ttk.Label(status_frame, textvariable=self.status_var).grid(row=0, column=1, sticky="w", padx=(4, 0))

        row += 1
        label_frame = ttk.LabelFrame(self.control_frame, text="Label filters")
        label_frame.grid(row=row, column=0, columnspan=3, sticky="nsew", pady=(10, 0))
        label_frame.columnconfigure(0, weight=1)
        label_frame.rowconfigure(1, weight=1)

        button_bar = ttk.Frame(label_frame)
        button_bar.grid(row=0, column=0, sticky="ew", padx=4, pady=4)
        button_bar.columnconfigure(0, weight=1)
        button_bar.columnconfigure(1, weight=1)
        ttk.Button(button_bar, text="Select all", command=self._select_all_labels).grid(row=0, column=0, sticky="ew", padx=(0, 4))
        ttk.Button(button_bar, text="Clear", command=self._clear_label_selection).grid(row=0, column=1, sticky="ew")

        listbox_frame = ttk.Frame(label_frame)
        listbox_frame.grid(row=1, column=0, sticky="nsew", padx=4, pady=(0, 4))
        listbox_frame.columnconfigure(0, weight=1)
        listbox_frame.rowconfigure(0, weight=1)
        self.labels_listbox = tk.Listbox(listbox_frame, selectmode=tk.MULTIPLE, exportselection=False, height=10)
        self.labels_listbox.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(listbox_frame, orient="vertical", command=self.labels_listbox.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.labels_listbox.configure(yscrollcommand=scrollbar.set)
        self.labels_listbox.bind("<<ListboxSelect>>", lambda _event: self._on_label_selection_changed())

        self._refresh_models(initial=True)
        self._refresh_cameras()

    def _register_bus_subscriptions(self) -> None:
        self._bus.subscribe(DETECTION_TOPIC, self._detection_queue.put)
        self._bus.subscribe(DEVICE_TOPIC, self._device_queue.put)
        self._bus.subscribe(ERROR_TOPIC, self._error_queue.put)

    def _refresh_models(self, initial: bool = False) -> None:
        models = self._list_models.execute(ensure=self.model_var.get())
        self.model_combo.configure(values=models)
        if initial and models:
            self.model_combo.set(models[0])
            self.model_var.set(models[0])
        self._load_labels()

    def _on_model_selected(self) -> None:
        self._load_labels()

    def _load_labels(self) -> None:
        path = self.model_var.get().strip()
        if not path:
            return
        try:
            labels = self._load_labels.execute(path)
        except Exception as exc:
            messagebox.showerror("Model labels", str(exc))
            return
        self.labels_listbox.delete(0, tk.END)
        for label in labels:
            self.labels_listbox.insert(tk.END, label)

    def _refresh_cameras(self) -> None:
        cameras = self._list_cameras.execute()
        if not cameras:
            self.camera_combo.configure(values=("No cameras detected",), state="disabled")
            self.camera_var.set("No cameras detected")
            return
        labels = []
        self._camera_lookup = {}
        selected_label = None
        for camera in cameras:
            resolution = camera.default_resolution
            res_text = f"{resolution.width}x{resolution.height}" if resolution else "Unknown"
            label = f"{camera.index}: {camera.name} ({res_text})"
            labels.append(label)
            self._camera_lookup[label] = camera
            if camera.index == self._config.initial_settings.camera_index:
                selected_label = label
        self.camera_combo.configure(values=labels, state="readonly")
        if selected_label:
            self.camera_combo.set(selected_label)
            self.camera_var.set(selected_label)
        else:
            self.camera_combo.set(labels[0])
            self.camera_var.set(labels[0])

    def _on_camera_selected(self) -> None:
        label = self.camera_var.get()
        camera = self._camera_lookup.get(label)
        if not camera:
            return
        resolution = getattr(camera, "default_resolution", None)
        if resolution and getattr(resolution, "width", 0) and getattr(resolution, "height", 0):
            self.frame_width_var.set(str(int(resolution.width)))
            self.frame_height_var.set(str(int(resolution.height)))

    def _select_all_labels(self) -> None:
        self.labels_listbox.select_set(0, tk.END)

    def _clear_label_selection(self) -> None:
        self.labels_listbox.select_clear(0, tk.END)

    def _on_label_selection_changed(self) -> None:
        pass

    def start_detection(self) -> None:
        request = self._build_settings_request()
        if request is None:
            return
        try:
            self._update_settings.execute(request)
        except Exception as exc:
            messagebox.showerror("Invalid settings", str(exc))
            return
        self._start_detection.execute()
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self._detection_running = True

    def stop_detection(self) -> None:
        self._stop_detection.execute()
        self.start_button.configure(state="normal")
        self.stop_button.configure(state="disabled")
        self._detection_running = False
        self.status_var.set("Idle")

    def _build_settings_request(self) -> UpdateSettingsRequest | None:
        try:
            camera_index = int((self.camera_var.get().split(":", 1)[0]).strip())
            frame_width = int(self.frame_width_var.get())
            frame_height = int(self.frame_height_var.get())
            target_fps = float(self.target_fps_var.get())
            inference_interval = int(self.inference_var.get())
            confidence = float(self.confidence_var.get())
            zoom = float(self.zoom_var.get())
        except ValueError:
            messagebox.showerror("Invalid settings", "Ensure numeric fields contain valid numbers")
            return None
        selected_indices = self.labels_listbox.curselection()
        labels = tuple(self.labels_listbox.get(i) for i in selected_indices)
        device = self.device_var.get()
        if device == "auto":
            device = None
        return UpdateSettingsRequest(
            model_path=self.model_var.get(),
            camera_index=camera_index,
            frame_width=frame_width,
            frame_height=frame_height,
            target_fps=target_fps,
            inference_interval=inference_interval,
            confidence_threshold=confidence,
            digital_zoom=zoom,
            device=device,
            selected_labels=labels,
        )

    def _schedule_python_log_update(self) -> None:
        try:
            while True:
                message = self._python_log_queue.get_nowait()
                self.python_logs.append(message)
        except queue.Empty:
            pass
        finally:
            self.root.after(200, self._schedule_python_log_update)

    def _schedule_detection_updates(self) -> None:
        try:
            while True:
                event = self._detection_queue.get_nowait()
                self.preview.update(event.frame)
                self.status_var.set(
                    f"FPS {event.fps:.1f} | Inference {event.inference_ms:.1f} ms | Detections {len(event.boxes)}"
                )
                self._detection_running = True
        except queue.Empty:
            pass
        finally:
            self.root.after(50, self._schedule_detection_updates)

    def _schedule_device_updates(self) -> None:
        try:
            while True:
                event = self._device_queue.get_nowait()
                description = getattr(event, "description", str(event))
                if "started" in description.lower():
                    self._detection_running = True
                    self.start_button.configure(state="disabled")
                    self.stop_button.configure(state="normal")
                if "stopped" in description.lower():
                    self._detection_running = False
                    self.start_button.configure(state="normal")
                    self.stop_button.configure(state="disabled")
                    self.status_var.set("Idle")
        except queue.Empty:
            pass
        finally:
            self.root.after(200, self._schedule_device_updates)

    def _schedule_error_updates(self) -> None:
        try:
            while True:
                event = self._error_queue.get_nowait()
                self._logger.error("Application error: %s", event.message, exc_info=event.exception)
                try:
                    messagebox.showerror("Error", event.message)
                except tk.TclError:
                    pass
        except queue.Empty:
            pass
        finally:
            self.root.after(500, self._schedule_error_updates)

    def _schedule_command_status_updates(self) -> None:
        try:
            while True:
                status = self._command_status_queue.get_nowait()
                if status == "refresh-position":
                    self._poller.trigger()
                else:
                    self.status_var.set(status)
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self._schedule_command_status_updates)

    def _schedule_gcode_log_updates(self) -> None:
        try:
            while True:
                message = self._gcode_log_queue.get_nowait()
                self.gcode_panel._on_log(message)
        except queue.Empty:
            pass
        finally:
            self.root.after(200, self._schedule_gcode_log_updates)

    def shutdown(self) -> None:
        try:
            self._stop_detection.execute()
        except Exception:
            pass
        self._dispatcher.stop()
        self._poller.stop()
        sys.stdout = self._original_stdout
        sys.stderr = self._original_stderr
        self.root.quit()

    def run(self) -> None:
        self.root.mainloop()
