import tkinter as tk
from tkinter import ttk
import asyncio, threading, inspect, traceback

from gui.widgets.InfoButton import InfoButton


class DropdownInput(tk.Frame):
    def __init__(self, master, items=None, label_text="", on_change=None, info_text: str | None = None, **combo_kwargs):
        super().__init__(master)
        self._on_change = on_change
        self._values_to_names = {}
        self._names_to_values = {}

        # default layout
        self.pack(padx=10, pady=10, fill="x")

        # Left label
        self._label = ttk.Label(self, text=label_text)
        self._label.pack(side="left", padx=(0, 5))

        # Combobox
        self._var = tk.StringVar()
        combo_kwargs.setdefault("state", "readonly")
        self._combo = ttk.Combobox(self, textvariable=self._var, **combo_kwargs)
        self._combo.pack(side="left", fill="x", expand=True)
        self._combo.bind("<<ComboboxSelected>>", self._on_selected)

        # Optional info button on the RIGHT
        if isinstance(info_text, str) and info_text.strip():
            title = f"{label_text} Explanation" if label_text else "Explanation"
            self._info_btn = InfoButton(self, title=title, message=info_text.strip())
            self._info_btn.pack(side="right", padx=(8, 0))
        else:
            self._info_btn = None

        # Populate with initial items
        self.set_items(items or [])

    # --- public API ---
    def get_value(self):
        return self._names_to_values.get(self._var.get(), None)

    def set_value(self, value):
        if value not in self._values_to_names:
            raise ValueError(f"value {value!r} not present in items")
        name = self._values_to_names[value]
        if self._var.get() != name:
            self._var.set(name)
            self._fire_on_change(value)

    def set_items(self, items):
        self._values_to_names.clear()
        self._names_to_values.clear()

        if not items:
            # show dummy entry and disable
            self._combo["values"] = ["(no values available)"]
            self._var.set("(no values available)")
            self._combo.state(["disabled"])
            return

        # build mappings and populate
        display_names = []
        for val, name in items:
            self._values_to_names[val] = name
            self._names_to_values[name] = val
            display_names.append(name)

        self._combo["values"] = display_names
        self._var.set(display_names[0])  # default to first item
        self._combo.state(["!disabled", "readonly"])
        self._fire_on_change(self.get_value())

    # --- internals ---
    def _on_selected(self, _event):
        self._fire_on_change(self.get_value())

    def _fire_on_change(self, value):
        cb = self._on_change
        if not callable(cb):
            return
        if inspect.iscoroutinefunction(cb):
            self._run_async(cb(value)); return
        try:
            maybe = cb(value)
        except Exception:
            traceback.print_exc(); return
        if inspect.iscoroutine(maybe):
            self._run_async(maybe)

    def _run_async(self, coro):
        def worker():
            try: asyncio.run(coro)
            except Exception: traceback.print_exc()
        threading.Thread(target=worker, daemon=True).start()

# Demo
if __name__ == "__main__":
    async def on_change_async(val):
        await asyncio.sleep(0.5)
        print("changed to:", val)

    root = tk.Tk()
    opts = [("pt", "Português"), ("en", "English"), ("es", "Español")]

    dd1 = DropdownInput(
        root, opts, label_text="Language:", on_change=on_change_async, width=18,
        info_text="Choose the UI language. This affects labels and messages only."
    )

    dd2 = DropdownInput(
        root, [], label_text="Empty:", on_change=on_change_async, width=18,
        info_text="No options available. Plug a device or load data to enable."
    )

    dd3 = DropdownInput(
        root, [], label_text="Empty:", on_change=on_change_async, width=18
    )

    root.mainloop()
