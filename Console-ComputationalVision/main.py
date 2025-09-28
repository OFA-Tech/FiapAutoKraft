from __future__ import annotations

import argparse
import logging
import queue
import sys
import threading
import time
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import messagebox, scrolledtext, ttk
from typing import Callable

import cv2
from PIL import Image, ImageTk

from services.GrblSender import GrblSender
from services.vision_service import VisionService


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="YOLOv12 console runner.")
    parser.add_argument(
        "--model-path",
        default="models/best.pt",
        help="Path to the YOLOv12 weights to be used for inference.",
    )
    parser.add_argument(
        "--camera-index",
        type=int,
        default=0,
        help="Index of the video capture device (0 for the first camera).",
    )
    parser.add_argument(
        "--frame-width",
        type=int,
        default=1280,
        help="Desired capture width. Use the native camera resolution when possible.",
    )
    parser.add_argument(
        "--frame-height",
        type=int,
        default=720,
        help="Desired capture height. Use the native camera resolution when possible.",
    )
    parser.add_argument(
        "--target-fps",
        type=float,
        default=30.0,
        help="Hint for the camera FPS. Some webcams might ignore this setting.",
    )
    parser.add_argument(
        "--inference-interval",
        type=int,
        default=3,
        help="Run a full YOLO inference every N frames to save resources.",
    )
    parser.add_argument(
        "--confidence-threshold",
        type=float,
        default=0.60,
        help="Minimum confidence value required to draw a bounding box.",
    )
    parser.add_argument(
        "--digital-zoom",
        type=float,
        default=1.0,
        help=(
            "Apply a digital zoom to the displayed frame. Values < 1.0 zoom out, "
            "values > 1.0 zoom in. The inference always runs on the original frame."
        ),
    )
    parser.add_argument(
        "--device",
        choices=("cpu", "cuda"),
        default=None,
        help="Manually select the inference device. Defaults to CUDA when available.",
    )
    parser.add_argument(
        "--window-name",
        default="YOLOv12 Detection",
        help="Title of the OpenCV preview window.",
    )
    return parser.parse_args()


@dataclass
class FieldSpec:
    label: str
    key: str
    caster: Callable[[str], object]


@dataclass
class CommandRequest:
    name: str
    execute: Callable[[], list[str]]
    refresh_position: bool = False
    status_text: str | None = None
    on_success: Callable[[], None] | None = None
    on_error: Callable[[Exception | None], None] | None = None


class TkQueueHandler(logging.Handler):
    def __init__(self, target_queue: queue.Queue[str]) -> None:
        super().__init__()
        self.target_queue = target_queue

    def emit(self, record: logging.LogRecord) -> None:  # pragma: no cover - GUI feedback
        try:
            message = self.format(record)
        except Exception:  # pragma: no cover - safety
            self.handleError(record)
            return
        self.target_queue.put(message)


class QueueStreamRedirector:
    """Redirect sys.stdout/sys.stderr writes into the GUI log queue."""

    def __init__(self, target_queue: queue.Queue[str], label: str) -> None:
        self.target_queue = target_queue
        self.label = label
        self._buffer = ""

    def write(self, message: str) -> None:  # pragma: no cover - GUI feedback helper
        if not message:
            return
        if not isinstance(message, str):
            message = str(message)
        normalised = message.replace("\r", "\n")
        if not normalised:
            return
        self._buffer += normalised
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            self._emit(line)

    def flush(self) -> None:  # pragma: no cover - GUI feedback helper
        if self._buffer:
            self._emit(self._buffer)
            self._buffer = ""

    def writelines(self, lines) -> None:  # pragma: no cover - GUI feedback helper
        for line in lines:
            self.write(line)

    def _emit(self, text: str) -> None:
        formatted = text.rstrip()
        if not formatted:
            return
        timestamp = time.strftime("%H:%M:%S")
        self.target_queue.put(f"{timestamp} - {self.label} - {formatted}")

    def close(self) -> None:  # pragma: no cover - GUI feedback helper
        self.flush()


class VisionGUI:
    def __init__(self, root: tk.Tk, initial_args: argparse.Namespace) -> None:
        self.root = root
        self.root.title(initial_args.window_name)
        self.initial_args = initial_args

        self._project_root = Path(__file__).resolve().parent
        self._field_specs = [
            FieldSpec("Frame width", "frame_width", int),
            FieldSpec("Frame height", "frame_height", int),
            FieldSpec("Inference interval", "inference_interval", int),
            FieldSpec("Confidence threshold", "confidence_threshold", float),
            FieldSpec("Digital zoom", "digital_zoom", float),
        ]

        self.window_title = initial_args.window_name
        fps_value = str(int(float(getattr(initial_args, "target_fps", 30))))
        if fps_value not in {"15", "30", "60"}:
            fps_value = "30"

        self.arg_vars: dict[str, tk.StringVar] = {}
        initial_map = {
            "model_path": getattr(initial_args, "model_path", ""),
            "camera_index": str(getattr(initial_args, "camera_index", 0)),
            "frame_width": str(getattr(initial_args, "frame_width", 0)),
            "frame_height": str(getattr(initial_args, "frame_height", 0)),
            "target_fps": fps_value,
            "inference_interval": str(getattr(initial_args, "inference_interval", 3)),
            "confidence_threshold": str(getattr(initial_args, "confidence_threshold", 0.6)),
            "digital_zoom": f"{float(getattr(initial_args, 'digital_zoom', 1.0)):.1f}",
            "window_name": self.window_title,
        }

        for key, value in initial_map.items():
            self.arg_vars[key] = tk.StringVar(value=value)

        self.device_var = tk.StringVar(value=initial_args.device or "auto")
        self.status_var = tk.StringVar(value="Idle")
        self.camera_choice_var = tk.StringVar()
        self.available_labels: list[str] = []
        self.selected_labels_cache: list[str] = []

        self.model_paths: list[str] = []
        self.camera_options: list[dict] = []

        self.serial_port_var = tk.StringVar()
        self.grbl_command_var = tk.StringVar()
        self.grbl_log_queue: queue.Queue[str] = queue.Queue()
        self.grbl_sender = GrblSender()
        self.grbl_reader_thread: threading.Thread | None = None
        self.grbl_reader_stop: threading.Event | None = None
        self._serial_ports_lookup: dict[str, dict] = {}
        self.grbl_coordinate_vars: dict[str, tk.StringVar] = {
            axis: tk.StringVar(value="0") for axis in ("x", "y", "z")
        }
        self.feedrate_var = tk.StringVar(value="200")
        self.feedrate_error_var = tk.StringVar(value="")
        self.command_status_var = tk.StringVar(value="")
        self.current_position_axis_vars: dict[str, tk.StringVar] = {
            axis: tk.StringVar(value="-") for axis in ("x", "y", "z")
        }

        self.frame_queue: queue.Queue = queue.Queue(maxsize=2)
        self.photo_image: ImageTk.PhotoImage | None = None
        self.video_canvas_image_id: int | None = None
        self.service: VisionService | None = None
        self.worker: threading.Thread | None = None
        self.stop_event: threading.Event | None = None
        self.running = False
        self.last_loaded_model: str = ""

        self.python_log_queue: queue.Queue[str] = queue.Queue()
        self.python_log_handler = TkQueueHandler(self.python_log_queue)
        self.python_log_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(levelname)s - %(message)s", "%H:%M:%S")
        )
        self.python_log_max_lines = 150
        root_logger = logging.getLogger()
        for handler in list(root_logger.handlers):
            root_logger.removeHandler(handler)
            handler.close()
        root_logger.addHandler(self.python_log_handler)
        root_logger.setLevel(logging.INFO)
        logging.captureWarnings(True)
        self.logger = logging.getLogger(__name__)
        self.grbl_sender.set_event_hook(self._on_grbl_event)

        self._original_stdout = sys.stdout
        self._original_stderr = sys.stderr
        self.stdout_redirector = QueueStreamRedirector(self.python_log_queue, "STDOUT")
        self.stderr_redirector = QueueStreamRedirector(self.python_log_queue, "STDERR")
        sys.stdout = self.stdout_redirector
        sys.stderr = self.stderr_redirector

        self._position_poll_stop = threading.Event()
        self._position_poll_wakeup = threading.Event()
        self._position_force_refresh = threading.Event()
        self._position_poll_thread: threading.Thread | None = None
        self._command_queue: queue.Queue = queue.Queue()
        self._command_worker_stop = threading.Event()
        self._command_worker_thread: threading.Thread | None = None
        self._command_inflight = threading.Event()

        self._build_layout()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._schedule_preview_update()
        self._schedule_grbl_log_update()
        self._schedule_python_log_update()
        self._start_background_workers()
        self._refresh_current_position_display(force=True)

    def _build_layout(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.columnconfigure(1, weight=3)
        self.root.rowconfigure(0, weight=1)

        control_frame = ttk.LabelFrame(self.root, text="Camera and AI Settings")
        control_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        control_frame.columnconfigure(1, weight=1)

        row = 0
        ttk.Label(control_frame, text="Model path").grid(row=row, column=0, sticky="w", pady=2)
        self.model_combobox = ttk.Combobox(
            control_frame,
            textvariable=self.arg_vars["model_path"],
            state="readonly",
        )
        self.model_combobox.grid(row=row, column=1, sticky="ew", pady=2)
        self.model_combobox.configure(postcommand=self._refresh_model_paths)
        self.model_combobox.bind("<<ComboboxSelected>>", lambda _event: self._on_model_selected())
        refresh_models_btn = ttk.Button(control_frame, text="🔃", width=3, command=self._on_model_refresh_clicked)
        refresh_models_btn.grid(row=row, column=2, padx=4)

        row += 1
        ttk.Label(control_frame, text="Camera").grid(row=row, column=0, sticky="w", pady=2)
        self.camera_combobox = ttk.Combobox(
            control_frame,
            textvariable=self.camera_choice_var,
            state="readonly",
        )
        self.camera_combobox.grid(row=row, column=1, sticky="ew", pady=2)
        self.camera_combobox.bind("<<ComboboxSelected>>", lambda _event: self._on_camera_selected())
        rescan_btn = ttk.Button(control_frame, text="🔃", width=3, command=self._populate_camera_combobox)
        rescan_btn.grid(row=row, column=2, padx=4)

        row += 1
        ttk.Label(control_frame, text="Target FPS").grid(row=row, column=0, sticky="w", pady=2)
        self.target_fps_combobox = ttk.Combobox(
            control_frame,
            textvariable=self.arg_vars["target_fps"],
            values=("15", "30", "60"),
            state="readonly",
        )
        self.target_fps_combobox.grid(row=row, column=1, sticky="ew", pady=2)
        if self.arg_vars["target_fps"].get() not in {"15", "30", "60"}:
            self.target_fps_combobox.set("30")

        row += 1
        ttk.Label(control_frame, text="Inference interval").grid(row=row, column=0, sticky="w", pady=2)
        self.inference_entry = ttk.Entry(control_frame, textvariable=self.arg_vars["inference_interval"])
        self.inference_entry.grid(row=row, column=1, sticky="ew", pady=2)
        inference_help = ttk.Button(
            control_frame,
            text="?",
            width=3,
            command=self._show_inference_interval_info,
        )
        inference_help.grid(row=row, column=2, padx=4)

        row += 1
        ttk.Label(control_frame, text="Confidence threshold").grid(row=row, column=0, sticky="w", pady=2)
        self.confidence_entry = ttk.Entry(control_frame, textvariable=self.arg_vars["confidence_threshold"])
        self.confidence_entry.grid(row=row, column=1, sticky="ew", pady=2)
        confidence_help = ttk.Button(
            control_frame,
            text="?",
            width=3,
            command=self._show_confidence_info,
        )
        confidence_help.grid(row=row, column=2, padx=4)

        row += 1
        ttk.Label(control_frame, text="Digital zoom").grid(row=row, column=0, sticky="w", pady=2)
        self.zoom_spinbox = ttk.Spinbox(
            control_frame,
            textvariable=self.arg_vars["digital_zoom"],
            from_=1.0,
            to=2.5,
            increment=0.1,
            format="%.1f",
        )
        self.zoom_spinbox.grid(row=row, column=1, sticky="ew", pady=2)

        row += 1
        ttk.Label(control_frame, text="Device").grid(row=row, column=0, sticky="w", pady=2)
        device_box = ttk.Combobox(
            control_frame,
            textvariable=self.device_var,
            values=("auto", "cpu", "cuda"),
            state="readonly",
        )
        device_box.grid(row=row, column=1, sticky="ew", pady=2)
        device_box.current(("auto", "cpu", "cuda").index(self.device_var.get() or "auto"))
        device_help = ttk.Button(
            control_frame,
            text="?",
            width=3,
            command=self._show_device_info,
        )
        device_help.grid(row=row, column=2, padx=4)

        row += 1
        button_frame = ttk.Frame(control_frame)
        button_frame.grid(row=row, column=0, columnspan=3, pady=(10, 0), sticky="ew")
        button_frame.columnconfigure(0, weight=1)
        button_frame.columnconfigure(1, weight=1)

        self.start_button = ttk.Button(button_frame, text="Start", command=self.start_stream)
        self.start_button.grid(row=0, column=0, sticky="ew", padx=(0, 5))

        self.stop_button = ttk.Button(button_frame, text="Stop", command=self.stop_stream, state="disabled")
        self.stop_button.grid(row=0, column=1, sticky="ew")

        status_row = row + 1
        status_frame = ttk.Frame(control_frame)
        status_frame.grid(row=status_row, column=0, columnspan=3, sticky="w", pady=(8, 0))
        ttk.Label(status_frame, text="State:").grid(row=0, column=0, sticky="w")
        ttk.Label(status_frame, textvariable=self.status_var).grid(row=0, column=1, sticky="w", padx=(4, 0))

        labels_row = status_row + 1
        control_frame.rowconfigure(labels_row, weight=1)
        label_frame = ttk.LabelFrame(control_frame, text="Label filters")
        label_frame.grid(row=labels_row, column=0, columnspan=3, sticky="nsew", pady=(10, 0))
        label_frame.columnconfigure(0, weight=1)
        label_frame.rowconfigure(1, weight=1)

        button_bar = ttk.Frame(label_frame)
        button_bar.grid(row=0, column=0, sticky="ew", padx=4, pady=4)
        button_bar.columnconfigure(0, weight=1)
        button_bar.columnconfigure(1, weight=1)

        select_all_btn = ttk.Button(button_bar, text="Select all", command=self._select_all_labels)
        select_all_btn.grid(row=0, column=0, sticky="ew", padx=(0, 4))

        clear_btn = ttk.Button(button_bar, text="Clear", command=self._clear_label_selection)
        clear_btn.grid(row=0, column=1, sticky="ew")

        listbox_frame = ttk.Frame(label_frame)
        listbox_frame.grid(row=1, column=0, sticky="nsew", padx=4, pady=(0, 4))
        listbox_frame.columnconfigure(0, weight=1)
        listbox_frame.rowconfigure(0, weight=1)

        self.labels_listbox = tk.Listbox(
            listbox_frame,
            selectmode=tk.MULTIPLE,
            exportselection=False,
            height=10,
        )
        self.labels_listbox.grid(row=0, column=0, sticky="nsew")
        self.labels_listbox.bind("<<ListboxSelect>>", lambda _event: self._apply_label_selection())

        scrollbar = ttk.Scrollbar(listbox_frame, orient="vertical", command=self.labels_listbox.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.labels_listbox.configure(yscrollcommand=scrollbar.set)

        grbl_row = labels_row + 1
        control_frame.rowconfigure(grbl_row, weight=1)
        grbl_frame = ttk.LabelFrame(control_frame, text="G-code Sender")
        grbl_frame.grid(row=grbl_row, column=0, columnspan=3, sticky="nsew", pady=(10, 0))
        grbl_frame.columnconfigure(1, weight=1)
        grbl_frame.rowconfigure(6, weight=1)

        ttk.Label(grbl_frame, text="Serial port").grid(row=0, column=0, sticky="w", pady=2, padx=4)
        self.serial_port_combo = ttk.Combobox(
            grbl_frame,
            textvariable=self.serial_port_var,
            state="readonly",
        )
        self.serial_port_combo.grid(row=0, column=1, sticky="ew", pady=2, padx=(0, 4))
        refresh_ports_btn = ttk.Button(grbl_frame, text="🔃", width=3, command=self._refresh_serial_ports)
        refresh_ports_btn.grid(row=0, column=2, pady=2, padx=4)

        button_bar = ttk.Frame(grbl_frame)
        button_bar.grid(row=1, column=0, columnspan=3, sticky="ew", padx=4, pady=4)
        button_bar.columnconfigure(0, weight=1)
        button_bar.columnconfigure(1, weight=1)
        self.connect_serial_button = ttk.Button(button_bar, text="Connect", command=self._connect_grbl)
        self.connect_serial_button.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        self.disconnect_serial_button = ttk.Button(
            button_bar,
            text="Disconnect",
            command=self._disconnect_grbl,
            state="disabled",
        )
        self.disconnect_serial_button.grid(row=0, column=1, sticky="ew")

        position_frame = ttk.Frame(grbl_frame)
        position_frame.grid(row=2, column=0, columnspan=3, sticky="ew", padx=4, pady=(4, 2))
        ttk.Label(position_frame, text="Current position").grid(row=0, column=0, sticky="w", padx=(0, 6))
        for idx, axis in enumerate(("x", "y", "z")):
            label_col = idx * 2 + 1
            entry_col = label_col + 1
            ttk.Label(position_frame, text=f"{axis.upper()}:").grid(row=0, column=label_col, sticky="w")
            ttk.Entry(
                position_frame,
                textvariable=self.current_position_axis_vars[axis],
                width=8,
                justify="right",
                state="readonly",
            ).grid(row=0, column=entry_col, sticky="w", padx=(0, 6))

        move_row = ttk.Frame(grbl_frame)
        move_row.grid(row=3, column=0, columnspan=3, sticky="ew", padx=4, pady=(0, 4))
        for idx, axis in enumerate(("x", "y", "z")):
            col = idx * 2
            ttk.Label(move_row, text=f"{axis.upper()}:").grid(row=0, column=col, sticky="w")
            ttk.Entry(move_row, textvariable=self.grbl_coordinate_vars[axis], width=6).grid(
                row=0,
                column=col + 1,
                sticky="w",
                padx=(0, 6),
            )

        feedrate_col = 6
        ttk.Label(move_row, text="Feedrate:").grid(row=0, column=feedrate_col, sticky="w")
        self.feedrate_entry = ttk.Entry(move_row, textvariable=self.feedrate_var, width=7)
        self.feedrate_entry.grid(row=0, column=feedrate_col + 1, sticky="w", padx=(0, 6))
        self.feedrate_error_label = ttk.Label(move_row, textvariable=self.feedrate_error_var, foreground="red")
        self.feedrate_error_label.grid(row=1, column=feedrate_col, columnspan=2, sticky="w", pady=(2, 0))

        button_start_col = feedrate_col + 2
        self.send_coordinates_button = ttk.Button(
            move_row,
            text="Send",
            command=self._send_coordinate_move,
            state="disabled",
        )
        self.send_coordinates_button.grid(row=0, column=button_start_col, sticky="ew", padx=(6, 4))

        self.home_button = ttk.Button(
            move_row,
            text="Home",
            command=self._home_grbl,
            state="disabled",
        )
        self.home_button.grid(row=0, column=button_start_col + 1, sticky="ew")

        move_row.columnconfigure(button_start_col + 2, weight=1)
        ttk.Label(move_row, textvariable=self.command_status_var, foreground="gray").grid(
            row=0,
            column=button_start_col + 2,
            sticky="w",
        )

        command_frame = ttk.Frame(grbl_frame)
        command_frame.grid(row=4, column=0, columnspan=3, sticky="ew", padx=4)
        command_frame.columnconfigure(0, weight=1)
        command_entry = ttk.Entry(command_frame, textvariable=self.grbl_command_var)
        command_entry.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        self.send_grbl_button = ttk.Button(
            command_frame,
            text="Send",
            command=self._send_grbl_command,
            state="disabled",
        )
        self.send_grbl_button.grid(row=0, column=1, sticky="ew", padx=(4, 0))

        ttk.Label(grbl_frame, text="G-code Logs").grid(row=5, column=0, columnspan=3, sticky="w", padx=4)
        self.grbl_log_text = scrolledtext.ScrolledText(grbl_frame, height=8, state="disabled", wrap="word")
        self.grbl_log_text.grid(row=6, column=0, columnspan=3, sticky="nsew", padx=4, pady=(0, 4))

        self._refresh_model_paths(initial=True)
        self._populate_camera_combobox()
        self._refresh_serial_ports()

        preview_frame = ttk.LabelFrame(self.root, text="Camera Preview")
        preview_frame.grid(row=0, column=1, sticky="nsew", padx=(0, 10), pady=10)
        preview_frame.rowconfigure(0, weight=3)
        preview_frame.rowconfigure(1, weight=2)
        preview_frame.columnconfigure(0, weight=1)

        video_canvas_container = ttk.Frame(preview_frame)
        video_canvas_container.grid(row=0, column=0, sticky="nsew")
        video_canvas_container.columnconfigure(0, weight=1)
        video_canvas_container.rowconfigure(0, weight=1)

        self.video_canvas = tk.Canvas(
            video_canvas_container,
            highlightthickness=0,
            borderwidth=0,
        )
        self.video_canvas.grid(row=0, column=0, sticky="nsew")
        self.video_canvas.bind("<Configure>", lambda _event: self._center_video_image())

        python_log_frame = ttk.LabelFrame(preview_frame, text="Python Logs")
        python_log_frame.grid(row=1, column=0, sticky="nsew", padx=6, pady=(6, 6))
        python_log_frame.columnconfigure(0, weight=1)
        python_log_frame.rowconfigure(0, weight=1)

        self.python_log_text = scrolledtext.ScrolledText(
            python_log_frame,
            height=10,
            state="disabled",
            wrap="word",
        )
        self.python_log_text.grid(row=0, column=0, sticky="nsew")

    def _on_model_refresh_clicked(self) -> None:
        self._refresh_model_paths()
        self._load_labels_if_possible()

    def _on_model_selected(self) -> None:
        selection = self.model_combobox.get().strip()
        self.arg_vars["model_path"].set(selection)
        self._load_labels_if_possible()

    def _ensure_model_in_list(self, path: str) -> None:
        if not path:
            return
        if path not in self.model_paths:
            self.model_paths.append(path)
            self.model_paths.sort()
        self.model_combobox.configure(values=self.model_paths)

    def _discover_model_files(self) -> list[str]:
        model_dir = self._project_root / "models"
        if not model_dir.exists():
            return []

        discovered: list[str] = []
        for file_path in sorted(model_dir.rglob("*.pt")):
            try:
                relative = file_path.relative_to(self._project_root)
                discovered.append(relative.as_posix())
            except ValueError:
                discovered.append(file_path.as_posix())
        return discovered

    def _refresh_model_paths(self, initial: bool = False) -> None:
        discovered = self._discover_model_files()
        extras = [path for path in self.model_paths if path not in discovered]
        combined = discovered + extras

        current = self.arg_vars["model_path"].get().strip()
        if current and current not in combined:
            combined.insert(0, current)

        self.model_paths = combined
        self.model_combobox.configure(values=self.model_paths)

        if not self.model_paths:
            self.model_combobox.set("")
            return

        if initial and not current:
            self.arg_vars["model_path"].set(self.model_paths[0])
            self.model_combobox.set(self.model_paths[0])
        elif current:
            self.model_combobox.set(current)

        self._load_labels_if_possible()

    def _populate_camera_combobox(self) -> None:
        self.camera_options = self._enumerate_cameras()
        if not self.camera_options:
            self.camera_combobox.configure(values=("No cameras detected",), state="disabled")
            self.camera_choice_var.set("No cameras detected")
            self.arg_vars["camera_index"].set("")
            return

        labels = [option["label"] for option in self.camera_options]
        self.camera_combobox.configure(values=labels, state="readonly")

        current_index = self.arg_vars["camera_index"].get()
        selected = None
        if current_index:
            for option in self.camera_options:
                if str(option["index"]) == current_index:
                    selected = option
                    break
        if selected is None:
            selected = self.camera_options[0]

        self.camera_choice_var.set(selected["label"])
        self._apply_camera_selection(selected)

    def _enumerate_cameras(self, max_devices: int = 10) -> list[dict]:
        cameras: list[dict] = []
        for index in range(max_devices):
            cap = cv2.VideoCapture(index)
            if not cap.isOpened():
                cap.release()
                v4l2_backend = getattr(cv2, "CAP_V4L2", None)
                if v4l2_backend is not None:
                    cap = cv2.VideoCapture(index, v4l2_backend)
                else:
                    cap = cv2.VideoCapture(index)
            if not cap.isOpened():
                cap.release()
                continue

            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
            backend_name = ""
            get_backend = getattr(cap, "getBackendName", None)
            if callable(get_backend):
                try:
                    backend_name = str(get_backend())
                except Exception:
                    backend_name = ""
            cap.release()

            if width <= 0:
                width = int(self.initial_args.frame_width)
            if height <= 0:
                height = int(self.initial_args.frame_height)

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
        return cameras

    def _resolve_camera_name(self, index: int) -> str:
        sysfs_name = Path(f"/sys/class/video4linux/video{index}/name")
        if sysfs_name.exists():
            try:
                return sysfs_name.read_text(encoding="utf-8").strip()
            except OSError:
                pass
        return f"Camera {index}"

    def _on_camera_selected(self) -> None:
        if not self.camera_options:
            return
        label = self.camera_choice_var.get()
        for option in self.camera_options:
            if option["label"] == label:
                self._apply_camera_selection(option)
                break

    def _apply_camera_selection(self, camera_info: dict) -> None:
        self.arg_vars["camera_index"].set(str(camera_info["index"]))
        width, height = camera_info.get("default_resolution", (0, 0))
        if width <= 0:
            width = int(self.initial_args.frame_width)
        if height <= 0:
            height = int(self.initial_args.frame_height)
        self.arg_vars["frame_width"].set(str(int(width)))
        self.arg_vars["frame_height"].set(str(int(height)))

    def _show_inference_interval_info(self) -> None:
        messagebox.showinfo(
            "Inference interval",
            (
                "Runs a full YOLO inference every N frames. Use lower values for "
                "maximum responsiveness or higher values to save computing resources."
            ),
        )

    def _show_confidence_info(self) -> None:
        messagebox.showinfo(
            "Confidence threshold",
            (
                "Sets the minimum detection confidence required before a bounding box "
                "is drawn. Increase the value to reduce false positives; decrease it "
                "to show more tentative detections."
            ),
        )

    def _show_device_info(self) -> None:
        messagebox.showinfo(
            "Device (Vision Compiler)",
            (
                "Selects the hardware used by the Vision Compiler for inference. "
                "Choose CUDA to leverage a compatible NVIDIA GPU, CPU to run on the "
                "processor, or Auto to pick the best option automatically."
            ),
        )

    def _refresh_serial_ports(self) -> None:
        ports = GrblSender.list_serial_ports()
        self._serial_ports_lookup = {}
        connected = self.grbl_sender.ser and self.grbl_sender.ser.is_open
        connected_label = None

        labels: list[str] = []
        for port in ports:
            description = port.get("description") or port.get("manufacturer") or "Unknown device"
            label = f"{port['device']} ({description})"
            labels.append(label)
            self._serial_ports_lookup[label] = port
            if port.get("device") == self.grbl_sender.port:
                connected_label = label

        if connected and self.grbl_sender.port and connected_label is None:
            connected_label = f"{self.grbl_sender.port} (connected)"
            labels.append(connected_label)
            self._serial_ports_lookup[connected_label] = {"device": self.grbl_sender.port}

        if not labels:
            if connected and self.grbl_sender.port:
                label = f"{self.grbl_sender.port} (connected)"
                self.serial_port_combo.configure(values=(label,), state="readonly")
                self.serial_port_var.set(label)
                self.serial_port_combo.set(label)
                self.connect_serial_button.configure(state="disabled")
            else:
                self.serial_port_combo.configure(values=("No ports detected",), state="disabled")
                self.serial_port_var.set("No ports detected")
                self.connect_serial_button.configure(state="disabled")
            return

        self.serial_port_combo.configure(values=labels, state="readonly")

        if connected_label:
            self.serial_port_var.set(connected_label)
            self.serial_port_combo.set(connected_label)
        else:
            current = self.serial_port_var.get()
            if current in labels:
                self.serial_port_combo.set(current)
            else:
                self.serial_port_var.set(labels[0])
                self.serial_port_combo.set(labels[0])

        if connected:
            self.connect_serial_button.configure(state="disabled")
        else:
            self.connect_serial_button.configure(state="normal")

        self._update_command_button_state()

    def _connect_grbl(self) -> None:
        if not self._serial_ports_lookup:
            messagebox.showwarning("No serial ports", "No serial ports are available to connect.")
            return

        selection = self.serial_port_var.get()
        port_info = self._serial_ports_lookup.get(selection)
        if not port_info:
            messagebox.showwarning("Select serial port", "Please choose a serial port to connect to.")
            return

        port = port_info["device"]
        if not self.grbl_sender.connect(port):
            messagebox.showerror("Connection failed", f"Unable to connect to {port}.")
            return

        self.grbl_sender.clear_trace()
        self._log_grbl(f"Connected to {port}")
        self.logger.info("Connected to %s", port)
        self.connect_serial_button.configure(state="disabled")
        self.disconnect_serial_button.configure(state="normal")
        self._update_command_button_state()
        self._start_grbl_reader()
        self._refresh_serial_ports()
        self._refresh_current_position_display(force=True)

    def _disconnect_grbl(self) -> None:
        port = self.grbl_sender.port
        self._stop_grbl_reader()
        self.grbl_sender.close_connection()
        self.grbl_sender.clear_trace()
        if port:
            self._log_grbl(f"Disconnected from {port}")
            self.logger.info("Disconnected from %s", port)
        self.disconnect_serial_button.configure(state="disabled")
        self.connect_serial_button.configure(state="normal")
        self._update_command_button_state()
        self._refresh_serial_ports()
        self._refresh_current_position_display(force=True)

    def _send_grbl_command(self) -> None:
        command = self.grbl_command_var.get().strip()
        if not command:
            return

        if not (self.grbl_sender.ser and self.grbl_sender.ser.is_open):
            messagebox.showerror("Serial not connected", "Connect to a serial port before sending commands.")
            return

        if self._command_inflight.is_set():
            messagebox.showwarning("Command in progress", "Wait for the current command to finish before sending another.")
            return

        self._log_grbl(f">> {command}")
        self.logger.info("Sent command: %s", command)
        try:
            self.grbl_sender.send_command(command, wait_for_ok=False)
        except Exception as exc:  # pragma: no cover - feedback for GUI users
            messagebox.showerror("Failed to send command", str(exc))
            return

        self.grbl_command_var.set("")

    def _validate_feedrate(self) -> float | None:
        raw = self.feedrate_var.get().strip()
        if not raw:
            raw = "200"
            self.feedrate_var.set(raw)
        try:
            value = float(raw)
        except ValueError:
            self.feedrate_error_var.set("Enter a valid number")
            return None
        if value <= 0 or value > 10000:
            self.feedrate_error_var.set("Must be between 0 and 10000")
            return None
        self.feedrate_error_var.set("")
        return value

    def _send_coordinate_move(self) -> None:
        if not (self.grbl_sender.ser and self.grbl_sender.ser.is_open):
            messagebox.showerror("Serial not connected", "Connect to a serial port before moving.")
            return

        coords: dict[str, float] = {}
        for axis in ("x", "y", "z"):
            raw = self.grbl_coordinate_vars[axis].get().strip()
            if not raw:
                coords[axis] = 0.0
                continue
            try:
                coords[axis] = float(raw)
            except ValueError:
                messagebox.showerror("Invalid coordinate", f"Enter a numeric value for {axis.upper()}.")
                return

        feedrate = self._validate_feedrate()
        if feedrate is None:
            return

        self._log_grbl(
            f">> Move X:{coords['x']:.3f} Y:{coords['y']:.3f} Z:{coords['z']:.3f} F:{feedrate:.1f}"
        )
        self.logger.info(
            "Move command issued X:%.3f Y:%.3f Z:%.3f at feedrate %.1f",
            coords["x"],
            coords["y"],
            coords["z"],
            feedrate,
        )
        request = CommandRequest(
            name="Move",
            execute=lambda x=coords["x"], y=coords["y"], z=coords["z"], f=feedrate: self.grbl_sender.send_coordinates(
                x,
                y,
                z,
                feedrate=f,
                timeout_s=4.0,
            ),
            refresh_position=True,
            status_text="Moving…",
        )
        self._dispatch_command(request)

    def _home_grbl(self) -> None:
        if not (self.grbl_sender.ser and self.grbl_sender.ser.is_open):
            messagebox.showerror("Serial not connected", "Connect to a serial port before homing.")
            return

        feedrate = self._validate_feedrate()
        if feedrate is None:
            return

        self._log_grbl(f">> Home F:{feedrate:.1f}")
        self.logger.info("Home command issued at feedrate %.1f", feedrate)

        def _on_success() -> None:
            for axis in ("x", "y", "z"):
                self.grbl_coordinate_vars[axis].set("0")

        request = CommandRequest(
            name="Home",
            execute=lambda f=feedrate: self.grbl_sender.center_core(feedrate=f, timeout_s=4.0),
            refresh_position=True,
            status_text="Homing…",
            on_success=_on_success,
        )
        self._dispatch_command(request)

    def _log_grbl(self, message: str) -> None:
        timestamp = time.strftime("%H:%M:%S")
        self.grbl_log_queue.put(f"[{timestamp}] {message}")

    def _format_event_payload(self, payload: dict) -> str:
        ordered = dict(payload)
        parts: list[str] = []
        for key in ("timestamp", "thread", "command", "port", "ser_id", "status"):
            if key in ordered:
                parts.append(f"{key}={ordered.pop(key)}")
        for key in sorted(ordered):
            parts.append(f"{key}={ordered[key]}")
        return " ".join(parts)

    def _emit_command_event(self, name: str, *, request: CommandRequest | None = None, **extra: object) -> None:
        ser = self.grbl_sender.ser
        payload: dict[str, object] = {
            "timestamp": f"{time.monotonic():.6f}",
            "thread": threading.current_thread().name,
            "port": self.grbl_sender.port,
        }
        if request is not None:
            payload["command"] = request.name
        if ser is not None:
            payload["ser_id"] = id(ser)
        payload.update(extra)
        self.logger.info("CMD_EVENT %s %s", name, self._format_event_payload(payload))

    def _on_grbl_event(self, name: str, payload: dict) -> None:
        payload = dict(payload)
        payload.setdefault("timestamp", time.monotonic())
        payload["timestamp"] = f"{float(payload["timestamp"]):.6f}"
        self.logger.info("GRBL_EVENT %s %s", name, self._format_event_payload(payload))

    def _append_grbl_log(self, message: str) -> None:
        self.grbl_log_text.configure(state="normal")
        self.grbl_log_text.insert(tk.END, message + "\n")
        self.grbl_log_text.see(tk.END)
        self.grbl_log_text.configure(state="disabled")

    def _schedule_grbl_log_update(self) -> None:
        try:
            while True:
                message = self.grbl_log_queue.get_nowait()
                self._append_grbl_log(message)
        except queue.Empty:
            pass
        finally:
            try:
                self.root.after(100, self._schedule_grbl_log_update)
            except tk.TclError:
                return

    def _append_python_log(self, message: str) -> None:
        if not hasattr(self, "python_log_text"):
            return
        widget = self.python_log_text
        previous_state = widget.cget("state")
        widget.configure(state="normal")
        current_view = widget.yview()
        should_scroll = current_view[1] >= 0.999
        widget.insert(tk.END, message + "\n")
        self._enforce_python_log_limit(widget)
        if should_scroll:
            widget.see(tk.END)
        else:
            widget.yview_moveto(current_view[0])
        widget.configure(state=previous_state)

    def _enforce_python_log_limit(self, widget: scrolledtext.ScrolledText) -> None:
        end_index = widget.index("end-1c")
        try:
            line_count = int(end_index.split(".")[0])
        except (ValueError, IndexError):
            return
        if line_count <= self.python_log_max_lines:
            return
        excess = line_count - self.python_log_max_lines
        widget.delete("1.0", f"{excess + 1}.0")

    def _schedule_python_log_update(self) -> None:
        try:
            while True:
                message = self.python_log_queue.get_nowait()
                self._append_python_log(message)
        except queue.Empty:
            pass
        finally:
            try:
                self.root.after(200, self._schedule_python_log_update)
            except tk.TclError:
                return

    def _start_background_workers(self) -> None:
        if self._position_poll_thread is None or not self._position_poll_thread.is_alive():
            self._position_poll_stop.clear()
            self._position_poll_thread = threading.Thread(
                target=self._position_poll_loop,
                name="PositionPoll",
                daemon=True,
            )
            self._position_poll_thread.start()

        if self._command_worker_thread is None or not self._command_worker_thread.is_alive():
            self._command_worker_stop.clear()
            self._command_worker_thread = threading.Thread(
                target=self._command_worker_loop,
                name="CommandWorker",
                daemon=True,
            )
            self._command_worker_thread.start()

    def _stop_background_workers(self) -> None:
        self._position_poll_stop.set()
        self._position_poll_wakeup.set()
        self._command_worker_stop.set()
        if self._command_worker_thread and self._command_worker_thread.is_alive():
            self._command_queue.put(None)

    def _position_poll_loop(self) -> None:
        next_run = time.monotonic()
        last_values: tuple[str, str, str] | None = None
        last_connected: bool | None = None
        while not self._position_poll_stop.is_set():
            now = time.monotonic()
            remaining = next_run - now
            if remaining > 0:
                triggered = self._position_poll_wakeup.wait(remaining)
                if triggered:
                    self._position_poll_wakeup.clear()
                    next_run = time.monotonic()
                    continue
            if self._position_poll_stop.is_set():
                break

            start = time.monotonic()
            connected = bool(self.grbl_sender.ser and self.grbl_sender.ser.is_open)
            busy = self._command_inflight.is_set()
            interval = 0.1 if connected else 1.0
            if connected and busy:
                interval = max(interval, 0.2)
            display_values: tuple[str, str, str] = ("-", "-", "-")
            raw_values: tuple[float, float, float] | None = None
            if connected and not busy:
                try:
                    raw_values = self.grbl_sender.sum_traces()
                except Exception:
                    raw_values = None
                if raw_values and any(abs(value) > 1e-6 for value in raw_values):
                    display_values = tuple(f"{float(value):.3f}" for value in raw_values)

            force = self._position_force_refresh.is_set()
            if force:
                self._position_force_refresh.clear()

            if connected and busy and not force:
                next_run = start + interval
                current = time.monotonic()
                if next_run < current:
                    next_run = current
                continue

            if force or display_values != last_values or connected != last_connected:
                last_values = display_values
                last_connected = connected
                try:
                    self.root.after(
                        0,
                        lambda vals=display_values, conn=connected: self._update_current_position_ui(vals, conn),
                    )
                except tk.TclError:
                    break

            next_run = start + interval
            current = time.monotonic()
            if next_run < current:
                next_run = current

        self._position_poll_wakeup.clear()
        self._position_poll_thread = None

    def _update_current_position_ui(self, values: tuple[str, str, str], connected: bool) -> None:
        if not hasattr(self, "current_position_axis_vars"):
            return
        for axis, value in zip(("x", "y", "z"), values):
            var = self.current_position_axis_vars.get(axis)
            if var is None:
                continue
            if var.get() != value:
                var.set(value)
        self._update_command_button_state()

    def _refresh_current_position_display(self, *, force: bool = False) -> None:
        if force:
            self._position_force_refresh.set()
        self._position_poll_wakeup.set()

    def _command_worker_loop(self) -> None:
        while not self._command_worker_stop.is_set():
            try:
                request: CommandRequest | None = self._command_queue.get(timeout=0.1)
            except queue.Empty:
                continue
            if request is None:
                self._command_queue.task_done()
                break

            start = time.monotonic()
            success = True
            responses: list[str] = []
            error: Exception | None = None
            self._emit_command_event("dequeue_at", request=request)
            try:
                responses = request.execute() or []
            except Exception as exc:  # pragma: no cover - hardware interactions
                success = False
                error = exc

            duration = time.monotonic() - start
            self._emit_command_event(
                "worker_complete",
                request=request,
                duration=f"{duration:.6f}",
                status="success" if success else "error",
            )
            if success:
                for line in responses:
                    self._log_grbl(f"<< {line}")
            else:
                message = f"{request.name} failed: {error}"
                self._log_grbl(message)
                self.logger.error(message)
                if isinstance(error, TimeoutError):
                    self.logger.error("%s timed out after %.2f s", request.name, duration)

            try:
                self.root.after(
                    0,
                    lambda req=request, ok=success, err=error: self._on_command_complete(req, ok, err),
                )
            except tk.TclError:
                break
            finally:
                self._command_queue.task_done()

        self._command_worker_thread = None

    def _on_command_complete(self, request: CommandRequest, success: bool, error: Exception | None) -> None:
        self._command_inflight.clear()
        if success:
            if request.on_success:
                request.on_success()
            self.command_status_var.set("")
        else:
            if request.on_error:
                request.on_error(error)
            error_text = f"{request.name} error"
            if isinstance(error, TimeoutError):
                error_text = f"{request.name} timeout"
            self.command_status_var.set(error_text)
            try:
                messagebox.showerror(error_text, str(error) if error else error_text)
            except tk.TclError:
                pass

        self._update_command_button_state()
        if request.refresh_position or not success:
            self._position_force_refresh.set()
            self._position_poll_wakeup.set()
        self._emit_command_event(
            "ui_updated",
            request=request,
            status="success" if success else "error",
        )

    def _update_command_button_state(self) -> None:
        if not hasattr(self, "send_coordinates_button"):
            return
        connected = bool(self.grbl_sender.ser and self.grbl_sender.ser.is_open)
        busy = self._command_inflight.is_set()
        state = "normal" if connected and not busy else "disabled"
        self.send_coordinates_button.configure(state=state)
        self.home_button.configure(state=state)
        general_state = "normal" if connected and not busy else "disabled"
        self.send_grbl_button.configure(state=general_state)

    def _dispatch_command(self, request: CommandRequest) -> None:
        if self._command_inflight.is_set():
            return
        self._command_inflight.set()
        status_text = request.status_text or f"{request.name}…"
        self.command_status_var.set(status_text)
        self._update_command_button_state()
        self._emit_command_event("enqueue_at", request=request)
        self._command_queue.put(request)

    def _start_grbl_reader(self) -> None:
        if self.grbl_reader_thread and self.grbl_reader_thread.is_alive():
            return

        self.grbl_reader_stop = threading.Event()
        self.grbl_reader_thread = threading.Thread(target=self._grbl_reader_loop, daemon=True)
        self.grbl_reader_thread.start()

    def _stop_grbl_reader(self) -> None:
        if self.grbl_reader_stop is not None:
            self.grbl_reader_stop.set()
        self.grbl_reader_stop = None
        self.grbl_reader_thread = None

    def _grbl_reader_loop(self) -> None:
        assert self.grbl_reader_stop is not None
        while not self.grbl_reader_stop.is_set():
            ser = self.grbl_sender.ser
            if not ser or not ser.is_open:
                time.sleep(0.1)
                continue

            if self._command_inflight.is_set():
                time.sleep(0.02)
                continue

            try:
                raw = ser.readline()
            except Exception as exc:  # pragma: no cover - hardware feedback
                self._log_grbl(f"Serial error: {exc}")
                self.grbl_reader_stop.set()
                break

            if not raw:
                continue

            text = raw.decode("utf-8", errors="replace").strip()
            if text:
                self._log_grbl(f"<< {text}")

    def _teardown_grbl(self) -> None:
        self._stop_grbl_reader()
        self.grbl_sender.close_connection()
        self.grbl_sender.clear_trace()
        self._refresh_current_position_display(force=True)
        self._update_command_button_state()

    def _teardown_logging(self) -> None:
        if hasattr(self, "stdout_redirector"):
            self.stdout_redirector.close()
        if hasattr(self, "stderr_redirector"):
            self.stderr_redirector.close()
        if hasattr(self, "_original_stdout"):
            sys.stdout = self._original_stdout
        if hasattr(self, "_original_stderr"):
            sys.stderr = self._original_stderr
        try:
            logging.getLogger().removeHandler(self.python_log_handler)
        except ValueError:
            pass
        self.python_log_handler.close()

    def _schedule_preview_update(self) -> None:
        try:
            frame = self.frame_queue.get_nowait()
        except queue.Empty:
            pass
        else:
            image = Image.fromarray(frame[:, :, ::-1])
            self.photo_image = ImageTk.PhotoImage(image=image)
            self._draw_video_frame()
        finally:
            self.root.after(30, self._schedule_preview_update)

    def _draw_video_frame(self) -> None:
        if not hasattr(self, "video_canvas"):
            return
        if self.photo_image is None:
            return

        canvas_width = self.video_canvas.winfo_width()
        canvas_height = self.video_canvas.winfo_height()

        if canvas_width <= 1 or canvas_height <= 1:
            self.video_canvas.update_idletasks()
            canvas_width = self.video_canvas.winfo_width()
            canvas_height = self.video_canvas.winfo_height()

        if self.video_canvas_image_id is None:
            self.video_canvas_image_id = self.video_canvas.create_image(
                canvas_width / 2,
                canvas_height / 2,
                image=self.photo_image,
                anchor="center",
            )
        else:
            self.video_canvas.itemconfig(self.video_canvas_image_id, image=self.photo_image)

        self._center_video_image()

    def _center_video_image(self) -> None:
        if not hasattr(self, "video_canvas"):
            return
        if self.video_canvas_image_id is None:
            return

        canvas_width = self.video_canvas.winfo_width()
        canvas_height = self.video_canvas.winfo_height()
        if canvas_width <= 1 or canvas_height <= 1:
            return

        self.video_canvas.coords(
            self.video_canvas_image_id,
            canvas_width / 2,
            canvas_height / 2,
        )

    def _collect_args(self) -> argparse.Namespace:
        values: dict[str, object] = {}

        model_path = self.arg_vars["model_path"].get().strip()
        if not model_path:
            raise ValueError("Model path cannot be empty.")
        values["model_path"] = model_path

        camera_index_raw = self.arg_vars["camera_index"].get().strip()
        if not camera_index_raw:
            raise ValueError("Camera index cannot be empty.")
        try:
            values["camera_index"] = int(camera_index_raw)
        except ValueError as exc:
            raise ValueError("Invalid value for Camera index.") from exc

        for spec in self._field_specs:
            raw_value = self.arg_vars[spec.key].get().strip()
            if not raw_value:
                raise ValueError(f"{spec.label} cannot be empty.")
            try:
                values[spec.key] = spec.caster(raw_value)
            except ValueError as exc:
                raise ValueError(f"Invalid value for {spec.label}.") from exc

        zoom_value = float(values.get("digital_zoom", 1.0))
        if not 1.0 <= zoom_value <= 2.5:
            raise ValueError("Digital zoom must be between 1.0 and 2.5.")
        values["digital_zoom"] = zoom_value

        target_fps_raw = self.arg_vars["target_fps"].get().strip()
        if not target_fps_raw:
            raise ValueError("Target FPS must be selected.")
        try:
            values["target_fps"] = float(target_fps_raw)
        except ValueError as exc:
            raise ValueError("Invalid value for Target FPS.") from exc

        device_value = self.device_var.get()
        values["device"] = None if device_value == "auto" else device_value
        values["window_name"] = self.window_title

        args = argparse.Namespace(**values)
        return args

    def start_stream(self) -> None:
        if self.running:
            return

        try:
            args = self._collect_args()
        except ValueError as exc:
            messagebox.showerror("Invalid arguments", str(exc))
            return

        window_title = getattr(args, "window_name", "YOLOv12 Detection") or "YOLOv12 Detection"
        self.root.title(window_title)

        try:
            self.service = VisionService(args)
            if not self.available_labels:
                labels = self.service.get_model_labels()
                self._populate_label_list(labels)
                self.last_loaded_model = self.arg_vars["model_path"].get().strip()
            self._apply_label_selection()
        except Exception as exc:  # pragma: no cover - feedback for GUI users
            messagebox.showerror("Failed to start vision service", str(exc))
            self.service = None
            return

        self.stop_event = threading.Event()
        self.running = True
        self.status_var.set("Running")
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")

        self.worker = threading.Thread(target=self._run_service, daemon=True)
        self.worker.start()

    def stop_stream(self) -> None:
        if not self.running:
            return

        if self.stop_event is not None:
            self.stop_event.set()
        self.status_var.set("Stopping...")
        self.stop_button.configure(state="disabled")

    def _run_service(self) -> None:
        assert self.service is not None
        assert self.stop_event is not None

        try:
            self.service.run(frame_callback=self._on_frame, stop_event=self.stop_event)
        except Exception as exc:  # pragma: no cover - feedback for GUI users
            message = str(exc)
            self.root.after(0, lambda msg=message: messagebox.showerror("Vision service error", msg))
            self.root.after(0, lambda msg=message: self.status_var.set(f"Error: {msg}"))
        finally:
            self.root.after(0, self._on_service_stopped)

    def _on_frame(self, frame) -> None:
        if self.stop_event and self.stop_event.is_set():
            return
        try:
            self.frame_queue.put_nowait(frame.copy())
        except queue.Full:
            try:
                _ = self.frame_queue.get_nowait()
            except queue.Empty:
                pass
            try:
                self.frame_queue.put_nowait(frame.copy())
            except queue.Full:
                pass

    def _on_service_stopped(self) -> None:
        self.running = False
        if not self.status_var.get().startswith("Error:"):
            self.status_var.set("Idle")
        self.start_button.configure(state="normal")
        self.stop_button.configure(state="disabled")
        self.service = None
        self.worker = None
        self.stop_event = None

    def _on_close(self) -> None:
        self._teardown_grbl()
        self._stop_background_workers()
        self._teardown_logging()
        if self.running:
            self.stop_stream()
            self.root.after(100, self._wait_for_thread_and_close)
        else:
            self.root.destroy()

    def _wait_for_thread_and_close(self) -> None:
        threads = [self.worker, self._command_worker_thread, self._position_poll_thread]
        if any(thread and thread.is_alive() for thread in threads):
            self.root.after(100, self._wait_for_thread_and_close)
            return
        self.root.destroy()

    def _load_labels_if_possible(self, *, require_feedback: bool = False) -> None:
        model_path = self.arg_vars["model_path"].get().strip()
        if not model_path:
            if require_feedback:
                messagebox.showwarning(
                    "Model path required",
                    "Please select a model path before loading labels.",
                )
            return

        if model_path == self.last_loaded_model:
            return

        resolved = Path(model_path)
        if not resolved.is_absolute():
            resolved = (self._project_root / model_path).resolve()

        if not resolved.exists():
            if require_feedback:
                messagebox.showerror(
                    "Model not found",
                    f"The selected model could not be located: {resolved}",
                )
            return

        try:
            labels = VisionService.discover_model_labels(model_path)
        except Exception as exc:  # pragma: no cover - user feedback
            if require_feedback:
                messagebox.showerror("Failed to load labels", str(exc))
            else:
                self.logger.error("Failed to load labels: %s", exc)
            return

        self.last_loaded_model = model_path
        self._populate_label_list(labels)
        self._apply_label_selection()
        self.logger.info("Loaded %d labels from %s", len(labels), resolved)

    def _populate_label_list(self, labels: list[str]) -> None:
        self.available_labels = labels
        self.labels_listbox.delete(0, tk.END)
        for label in labels:
            self.labels_listbox.insert(tk.END, label)

        if not self.selected_labels_cache:
            return

        lookup = {label: index for index, label in enumerate(labels)}
        for label in self.selected_labels_cache:
            index = lookup.get(label)
            if index is not None:
                self.labels_listbox.selection_set(index)

    def _get_selected_labels(self) -> list[str]:
        selection = self.labels_listbox.curselection()
        return [self.labels_listbox.get(index) for index in selection]

    def _apply_label_selection(self) -> None:
        if not hasattr(self, "labels_listbox"):
            return

        selected = self._get_selected_labels()
        self.selected_labels_cache = selected

        if not self.service:
            return

        try:
            self.service.select_labels(selected or None)
        except ValueError as exc:  # pragma: no cover - GUI feedback
            messagebox.showerror("Invalid label selection", str(exc))

    def _select_all_labels(self) -> None:
        for index in range(self.labels_listbox.size()):
            self.labels_listbox.selection_set(index)
        self._apply_label_selection()

    def _clear_label_selection(self) -> None:
        self.labels_listbox.selection_clear(0, tk.END)
        self._apply_label_selection()


def main() -> int:
    args = parse_arguments()
    root = tk.Tk()
    VisionGUI(root, args)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
