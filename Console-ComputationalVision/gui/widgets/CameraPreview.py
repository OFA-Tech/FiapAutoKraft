import tkinter as tk
from tkinter import ttk
import threading, time
import cv2
import numpy as np
from PIL import Image, ImageTk


class CameraPreview(tk.Frame):
    def __init__(self, master, width=640, height=360, fps=30,
                 capture: cv2.VideoCapture | None = None, title: str = "Preview", **kwargs):
        super().__init__(master, **kwargs)
        self._width_px, self._height_px = int(width), int(height)
        self._period_ms = max(1, int(1000 / max(1, int(fps))))
        self._cap = capture
        self._running = False
        self._thread = None
        self._lock = threading.Lock()
        self._latest_bgr = None
        self._tk_img = None

        # default layout
        self.pack(padx=10, pady=10, fill="both", expand=True)

        # header + image area
        self._title_lbl = ttk.Label(self, text=title)
        self._title_lbl.pack(anchor="w", pady=(0, 6))

        self._image_lbl = ttk.Label(self)
        self._image_lbl.pack(fill="both", expand=True)

        self._show_black()
        self.after(self._period_ms, self._ui_tick)

        # auto-start if provided capture is open
        if self._cap is not None and self._cap.isOpened():
            self.start()

    # ---------------- public API ----------------
    def set_capture(self, capture: cv2.VideoCapture | None):
        """Swap the capture object (does not release the old one)."""
        was_running = self._running
        self.stop()
        self._cap = capture
        if was_running and self._cap is not None and self._cap.isOpened():
            self.start()
        else:
            self._show_black()

    def get_capture(self):
        return self._cap

    def set_title(self, title: str):
        self._title_lbl.config(text=title)

    def start(self):
        """Start preview if capture is opened; otherwise show black."""
        if self._running:
            return
        if self._cap is None or not self._cap.isOpened():
            self._show_black()
            return
        self._running = True
        self._thread = threading.Thread(target=self._reader_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop preview (does NOT release the capture)."""
        self._running = False
        t = self._thread
        if t and t.is_alive():
            t.join(timeout=1.0)
        self._thread = None
        self._latest_bgr = None
        self._show_black()

    # --------------- internals ------------------
    def _reader_loop(self):
        while self._running and self._cap and self._cap.isOpened():
            ok, frame = self._cap.read()
            if not ok:
                time.sleep(0.01)
                continue
            with self._lock:
                self._latest_bgr = frame

    def _ui_tick(self):
        try:
            frame = None
            with self._lock:
                if self._latest_bgr is not None:
                    frame = self._latest_bgr.copy()

            if frame is None:
                # keep whatever is currently displayed (black at init/stop)
                pass
            else:
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                if (rgb.shape[1], rgb.shape[0]) != (self._width_px, self._height_px):
                    rgb = cv2.resize(rgb, (self._width_px, self._height_px), interpolation=cv2.INTER_AREA)
                img = Image.fromarray(rgb)
                self._tk_img = ImageTk.PhotoImage(img)
                self._image_lbl.configure(image=self._tk_img)
        finally:
            if self.winfo_exists():
                self.after(self._period_ms, self._ui_tick)

    def _show_black(self):
        black = np.zeros((self._height_px, self._width_px, 3), dtype=np.uint8)
        img = Image.fromarray(black)
        self._tk_img = ImageTk.PhotoImage(img)
        self._image_lbl.configure(image=self._tk_img)

    def destroy(self):
        try:
            self.stop()
        finally:
            super().destroy()

if __name__ == "__main__":
    root = tk.Tk()
    root.title("CameraPreview (param-driven)")

    # Not opened yet -> stays black
    cap0 = cv2.VideoCapture(0)  # try a real index
    if not cap0.isOpened():
        cap0 = None  # simulate unavailable camera

    preview = CameraPreview(root, width=640, height=360, fps=30,
                            capture=cap0, title="Camera 0")

    # buttons just to play with it
    btns = ttk.Frame(root); btns.pack(pady=8)
    ttk.Button(btns, text="Start", command=preview.start).pack(side="left", padx=5)
    ttk.Button(btns, text="Stop", command=preview.stop).pack(side="left", padx=5)
    ttk.Button(btns, text="Set camera 1",
               command=lambda: preview.set_capture(cv2.VideoCapture(1))).pack(side="left", padx=5)
    ttk.Button(btns, text="Clear camera",
               command=lambda: preview.set_capture(None)).pack(side="left", padx=5)

    root.mainloop()
