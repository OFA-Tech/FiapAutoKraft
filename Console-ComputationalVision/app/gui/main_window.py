"""Tkinter GUI used to interact with the inference pipeline."""

from __future__ import annotations

import queue
import threading
import time
import tkinter as tk
from tkinter import ttk
from typing import Sequence

from app.container import ApplicationContainer
from services.use_cases import VisionInferenceRequest, VisionInferenceResponse


class VisionApp:
    """Minimal operator console inspired by the legacy Tkinter interface."""

    def __init__(
        self,
        root: tk.Tk,
        container: ApplicationContainer,
        *,
        initial_labels: Sequence[str] | None = None,
    ) -> None:
        self.root = root
        self.container = container
        self.container.ensure_configured()

        self.root.title("Console Computational Vision")
        self.root.geometry("900x500")

        self._results_queue: "queue.Queue[VisionInferenceResponse | None]" = queue.Queue()
        self._worker: threading.Thread | None = None
        self._stop_event = threading.Event()

        self.label_filter_var = tk.StringVar(value=", ".join(initial_labels or ()))
        self.status_var = tk.StringVar(value="Idle")

        self._build_layout()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._schedule_queue_poll()

    # ------------------------------------------------------------------
    # UI construction helpers
    def _build_layout(self) -> None:
        main = ttk.Frame(self.root, padding=10)
        main.pack(fill=tk.BOTH, expand=True)
        main.columnconfigure(0, weight=1)
        main.rowconfigure(1, weight=1)

        controls = ttk.Frame(main)
        controls.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        controls.columnconfigure(1, weight=1)

        ttk.Label(controls, text="Label filter (comma separated)").grid(row=0, column=0, sticky="w")
        entry = ttk.Entry(controls, textvariable=self.label_filter_var)
        entry.grid(row=0, column=1, sticky="ew", padx=(8, 0))

        self.start_button = ttk.Button(controls, text="Start", command=self.start_stream)
        self.start_button.grid(row=0, column=2, padx=(10, 0))

        self.stop_button = ttk.Button(controls, text="Stop", command=self.stop_stream, state=tk.DISABLED)
        self.stop_button.grid(row=0, column=3, padx=(6, 0))

        ttk.Label(controls, textvariable=self.status_var).grid(row=0, column=4, padx=(12, 0))

        columns = ("label", "confidence", "bbox", "center")
        self.tree = ttk.Treeview(main, columns=columns, show="headings", height=18)
        self.tree.grid(row=1, column=0, sticky="nsew")
        self.tree.heading("label", text="Label")
        self.tree.heading("confidence", text="Confidence")
        self.tree.heading("bbox", text="Bounding Box")
        self.tree.heading("center", text="Center")
        for column, width in ("label", 120), ("confidence", 100), ("bbox", 220), ("center", 120):
            self.tree.column(column, width=width)

        scrollbar = ttk.Scrollbar(main, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=1, column=1, sticky="ns")

    # ------------------------------------------------------------------
    # Button callbacks
    def start_stream(self) -> None:
        if self._worker and self._worker.is_alive():
            return
        self._stop_event.clear()
        self.status_var.set("Running")
        self.start_button.configure(state=tk.DISABLED)
        self.stop_button.configure(state=tk.NORMAL)
        self._worker = threading.Thread(target=self._run_inference_loop, daemon=True)
        self._worker.start()

    def stop_stream(self) -> None:
        self._stop_event.set()
        self.status_var.set("Stopping...")
        self.start_button.configure(state=tk.NORMAL)
        self.stop_button.configure(state=tk.DISABLED)

    # ------------------------------------------------------------------
    # Background worker
    def _run_inference_loop(self) -> None:
        while not self._stop_event.is_set():
            labels = [label.strip() for label in self.label_filter_var.get().split(",") if label.strip()]
            with self.container.enter_scope("run") as scope:
                use_case = scope.vision_inference_use_case()
                response = use_case.execute(VisionInferenceRequest(selected_labels=labels or None))
            self._results_queue.put(response)
            time.sleep(0.5)
        self._results_queue.put(None)  # Signal completion

    # ------------------------------------------------------------------
    # Result handling
    def _schedule_queue_poll(self) -> None:
        self.root.after(100, self._poll_queue)

    def _poll_queue(self) -> None:
        try:
            while True:
                result = self._results_queue.get_nowait()
                if result is None:
                    self.status_var.set("Idle")
                    continue
                self._apply_results(result)
        except queue.Empty:
            pass
        finally:
            self._schedule_queue_poll()

    def _apply_results(self, response: VisionInferenceResponse) -> None:
        self.tree.delete(*self.tree.get_children())
        for detection in response.detections:
            bbox = detection.bounding_box.as_tuple()
            self.tree.insert(
                "",
                tk.END,
                values=(
                    detection.label,
                    f"{detection.confidence:.2f}",
                    f"({bbox[0]}, {bbox[1]}, {bbox[2]}, {bbox[3]})",
                    f"({detection.center[0]}, {detection.center[1]})",
                ),
            )
        self.status_var.set(f"Last batch: {response.total} detections")

    # ------------------------------------------------------------------
    def _on_close(self) -> None:
        self.stop_stream()
        self.root.after(200, self.root.destroy)


__all__ = ["VisionApp"]
