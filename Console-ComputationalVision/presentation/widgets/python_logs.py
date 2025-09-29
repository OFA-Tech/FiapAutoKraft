from __future__ import annotations

import tkinter as tk
from tkinter import scrolledtext

from shared.logging_utils import append_with_limit


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
        append_with_limit(self.text, message, self.max_lines)
