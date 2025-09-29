from __future__ import annotations

import tkinter as tk
from tkinter import scrolledtext


class PythonLogsWidget:
    def __init__(self, parent: tk.Widget, max_lines: int = 150) -> None:
        self.frame = tk.Frame(parent)
        self.frame.grid(row=0, column=0, sticky="nsew")
        self.frame.rowconfigure(0, weight=1)
        self.frame.columnconfigure(0, weight=1)

        self.text = scrolledtext.ScrolledText(self.frame, height=10, state="disabled", wrap="word")
        self.text.grid(row=0, column=0, sticky="nsew")
        self.max_lines = max_lines

    def widget(self) -> tk.Widget:
        return self.frame

    def append(self, message: str) -> None:
        self.text.configure(state="normal")
        current_view = self.text.yview()
        should_scroll = current_view[1] >= 0.999
        self.text.insert(tk.END, message + "\n")
        self._enforce_limit()
        if should_scroll:
            self.text.see(tk.END)
        else:
            self.text.yview_moveto(current_view[0])
        self.text.configure(state="disabled")

    def _enforce_limit(self) -> None:
        end_index = self.text.index("end-1c")
        try:
            line_count = int(end_index.split(".")[0])
        except (ValueError, IndexError):
            return
        if line_count <= self.max_lines:
            return
        excess = line_count - self.max_lines
        self.text.delete("1.0", f"{excess + 1}.0")
