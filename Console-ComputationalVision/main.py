from __future__ import annotations

import argparse
import queue
import threading
import tkinter as tk
from dataclasses import dataclass
from tkinter import filedialog, messagebox, ttk
from typing import Callable

from PIL import Image, ImageTk

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
        default=1,
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


class VisionGUI:
    def __init__(self, root: tk.Tk, initial_args: argparse.Namespace) -> None:
        self.root = root
        self.root.title(initial_args.window_name)
        self.initial_args = initial_args

        self._field_specs = [
            FieldSpec("Model path", "model_path", str),
            FieldSpec("Camera index", "camera_index", int),
            FieldSpec("Frame width", "frame_width", int),
            FieldSpec("Frame height", "frame_height", int),
            FieldSpec("Target FPS", "target_fps", float),
            FieldSpec("Inference interval", "inference_interval", int),
            FieldSpec("Confidence threshold", "confidence_threshold", float),
            FieldSpec("Digital zoom", "digital_zoom", float),
            FieldSpec("Window title", "window_name", str),
        ]

        self.arg_vars: dict[str, tk.StringVar] = {}
        for spec in self._field_specs:
            value = getattr(initial_args, spec.key)
            if value is None:
                value = ""
            self.arg_vars[spec.key] = tk.StringVar(value=str(value))

        self.device_var = tk.StringVar(value=initial_args.device or "auto")
        self.status_var = tk.StringVar(value="Idle")

        self.frame_queue: queue.Queue = queue.Queue(maxsize=2)
        self.photo_image: ImageTk.PhotoImage | None = None
        self.service: VisionService | None = None
        self.worker: threading.Thread | None = None
        self.stop_event: threading.Event | None = None
        self.running = False

        self._build_layout()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._schedule_preview_update()

    def _build_layout(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.columnconfigure(1, weight=3)
        self.root.rowconfigure(0, weight=1)

        control_frame = ttk.LabelFrame(self.root, text="Settings")
        control_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        control_frame.columnconfigure(1, weight=1)

        for row, spec in enumerate(self._field_specs):
            ttk.Label(control_frame, text=spec.label).grid(row=row, column=0, sticky="w", pady=2)
            entry = ttk.Entry(control_frame, textvariable=self.arg_vars[spec.key])
            entry.grid(row=row, column=1, sticky="ew", pady=2)
            if spec.key == "model_path":
                browse_btn = ttk.Button(control_frame, text="Browse", command=self._browse_model)
                browse_btn.grid(row=row, column=2, padx=4)

        device_row = len(self._field_specs)
        ttk.Label(control_frame, text="Device").grid(row=device_row, column=0, sticky="w", pady=2)
        device_box = ttk.Combobox(
            control_frame,
            textvariable=self.device_var,
            values=("auto", "cpu", "cuda"),
            state="readonly",
        )
        device_box.grid(row=device_row, column=1, sticky="ew", pady=2)
        device_box.current(("auto", "cpu", "cuda").index(self.device_var.get() or "auto"))

        button_row = device_row + 1
        button_frame = ttk.Frame(control_frame)
        button_frame.grid(row=button_row, column=0, columnspan=3, pady=(10, 0), sticky="ew")
        button_frame.columnconfigure(0, weight=1)
        button_frame.columnconfigure(1, weight=1)

        self.start_button = ttk.Button(button_frame, text="Start", command=self.start_stream)
        self.start_button.grid(row=0, column=0, sticky="ew", padx=(0, 5))

        self.stop_button = ttk.Button(button_frame, text="Stop", command=self.stop_stream, state="disabled")
        self.stop_button.grid(row=0, column=1, sticky="ew")

        status_row = button_row + 1
        ttk.Label(control_frame, textvariable=self.status_var).grid(
            row=status_row, column=0, columnspan=3, sticky="w", pady=(8, 0)
        )

        preview_frame = ttk.LabelFrame(self.root, text="Camera Preview")
        preview_frame.grid(row=0, column=1, sticky="nsew", padx=(0, 10), pady=10)
        preview_frame.rowconfigure(0, weight=1)
        preview_frame.columnconfigure(0, weight=1)

        self.video_label = ttk.Label(preview_frame)
        self.video_label.grid(row=0, column=0, sticky="nsew")

    def _browse_model(self) -> None:
        path = filedialog.askopenfilename(title="Select model file")
        if path:
            self.arg_vars["model_path"].set(path)

    def _schedule_preview_update(self) -> None:
        try:
            frame = self.frame_queue.get_nowait()
        except queue.Empty:
            pass
        else:
            image = Image.fromarray(frame[:, :, ::-1])
            self.photo_image = ImageTk.PhotoImage(image=image)
            self.video_label.configure(image=self.photo_image)
        finally:
            self.root.after(30, self._schedule_preview_update)

    def _collect_args(self) -> argparse.Namespace:
        values: dict[str, object] = {}
        for spec in self._field_specs:
            raw_value = self.arg_vars[spec.key].get().strip()
            if not raw_value:
                raise ValueError(f"{spec.label} cannot be empty.")
            if spec.caster is str:
                values[spec.key] = raw_value
            else:
                try:
                    values[spec.key] = spec.caster(raw_value)
                except ValueError as exc:
                    raise ValueError(f"Invalid value for {spec.label}.") from exc

        device_value = self.device_var.get()
        values["device"] = None if device_value == "auto" else device_value

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
            self.root.after(0, lambda: messagebox.showerror("Vision service error", str(exc)))
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
        self.status_var.set("Idle")
        self.start_button.configure(state="normal")
        self.stop_button.configure(state="disabled")
        self.service = None
        self.worker = None
        self.stop_event = None

    def _on_close(self) -> None:
        if self.running:
            self.stop_stream()
            self.root.after(100, self._wait_for_thread_and_close)
        else:
            self.root.destroy()

    def _wait_for_thread_and_close(self) -> None:
        if self.worker and self.worker.is_alive():
            self.root.after(100, self._wait_for_thread_and_close)
            return
        self.root.destroy()


def main() -> int:
    args = parse_arguments()
    root = tk.Tk()
    VisionGUI(root, args)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
