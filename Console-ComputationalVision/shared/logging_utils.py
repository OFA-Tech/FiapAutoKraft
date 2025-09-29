"""Utilities for routing log output into Tkinter widgets."""

from __future__ import annotations

from tkinter import Text


def append_with_limit(text_widget: Text, message: str, max_lines: int = 150) -> None:
    """Append ``message`` to ``text_widget`` while enforcing a FIFO line cap.

    The widget's scroll position is preserved if the user is looking away from
    the bottom; otherwise the view automatically scrolls to the end. The widget
    is temporarily switched to ``state="normal"`` so it can be modified.
    """

    text_widget.configure(state="normal")
    view = text_widget.yview()
    should_scroll = view[1] >= 0.999
    text_widget.insert("end", message + "\n")
    _trim_lines(text_widget, max_lines)
    if should_scroll:
        text_widget.see("end")
    else:
        text_widget.yview_moveto(view[0])
    text_widget.configure(state="disabled")


def _trim_lines(text_widget: Text, max_lines: int) -> None:
    """Remove the oldest lines so the widget never exceeds ``max_lines``."""

    end_index = text_widget.index("end-1c")
    try:
        line_count = int(end_index.split(".")[0])
    except (ValueError, IndexError):
        return
    if line_count <= max_lines:
        return
    excess = line_count - max_lines
    text_widget.delete("1.0", f"{excess + 1}.0")
