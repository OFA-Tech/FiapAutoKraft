from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass

from PIL import Image, ImageTk

from domain.camera.camera import Frame


@dataclass
class CanvasSize:
    width: int
    height: int


class CameraPreview:
    def __init__(self, parent: tk.Widget) -> None:
        self.container = tk.Frame(parent)
        self.container.grid(row=0, column=0, sticky="nsew")
        self.container.rowconfigure(0, weight=1)
        self.container.columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(self.container, highlightthickness=0, borderwidth=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.canvas.bind("<Configure>", lambda _event: self._redraw())
        self._photo: ImageTk.PhotoImage | None = None
        self._image_id: int | None = None
        self._last_frame: Frame | None = None

    def widget(self) -> tk.Widget:
        return self.container

    def update(self, frame: Frame) -> None:
        self._last_frame = frame
        self._render_frame(frame)

    def _render_frame(self, frame: Frame) -> None:
        canvas_size = self._current_canvas_size()
        if canvas_size.width <= 0 or canvas_size.height <= 0:
            return
        image = self._frame_to_image(frame, canvas_size)
        if image is None:
            return
        self._photo = ImageTk.PhotoImage(image=image)
        if self._image_id is None:
            self._image_id = self.canvas.create_image(
                canvas_size.width // 2,
                canvas_size.height // 2,
                image=self._photo,
            )
        else:
            self.canvas.itemconfig(self._image_id, image=self._photo)
            self.canvas.coords(
                self._image_id,
                canvas_size.width // 2,
                canvas_size.height // 2,
            )

    def _frame_to_image(self, frame: Frame, canvas_size: CanvasSize) -> Image.Image | None:
        data = frame.data
        if data is None:
            return None
        rgb = data[..., ::-1]
        image = Image.fromarray(rgb)
        width, height = image.size
        scale = min(canvas_size.width / width, canvas_size.height / height)
        if scale < 1 or scale > 1:
            new_size = (max(1, int(width * scale)), max(1, int(height * scale)))
            image = image.resize(new_size, Image.Resampling.LANCZOS)
        return image

    def _current_canvas_size(self) -> CanvasSize:
        return CanvasSize(width=int(self.canvas.winfo_width()), height=int(self.canvas.winfo_height()))

    def _redraw(self) -> None:
        if self._last_frame is not None:
            self._render_frame(self._last_frame)
