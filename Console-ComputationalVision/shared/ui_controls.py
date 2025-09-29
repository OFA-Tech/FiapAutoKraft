"""Helpers shared by Tkinter presentation widgets."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
import tkinter as tk
from tkinter import ttk


def update_combobox_options(
    combo: ttk.Combobox,
    variable: tk.StringVar,
    options: Sequence[str],
    *,
    placeholder: str = "No options available",
    preserve_selection: bool = True,
    empty_state: str = "disabled",
    value_state: str = "readonly",
) -> None:
    """Populate ``combo`` with ``options`` while preserving the selection."""

    if options:
        combo.configure(values=tuple(options), state=value_state)
        current = variable.get() if preserve_selection else ""
        if current not in options:
            current = options[0]
        combo.set(current)
        variable.set(current)
    else:
        combo.configure(values=(placeholder,), state=empty_state)
        combo.set(placeholder)
        variable.set(placeholder)


def bind_combobox_selection(combo: ttk.Combobox, callback: Callable[[str], None]) -> None:
    """Invoke ``callback`` whenever ``combo`` selection changes."""

    def _handler(_event: object) -> None:
        callback(combo.get())

    combo.bind("<<ComboboxSelected>>", _handler)


def set_group_state(widgets: Iterable[tk.Widget], *, enabled: bool) -> None:
    """Enable or disable an iterable of Tk widgets."""

    state = "normal" if enabled else "disabled"
    for widget in widgets:
        if widget.winfo_exists():
            widget.configure(state=state)


def safe_configure(widget: tk.Widget, **kwargs: object) -> None:
    """Configure ``widget`` only if it still exists (avoids race conditions)."""

    if widget.winfo_exists():
        widget.configure(**kwargs)
