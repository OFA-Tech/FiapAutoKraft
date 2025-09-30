import tkinter as tk
from tkinter import ttk
import asyncio, threading, inspect, traceback

from gui.widgets.InfoButton import InfoButton


class TextInput(tk.Frame):
    def __init__(
        self,
        master,
        label_text: str = "",
        on_change=None,
        on_submit=None,
        info_text: str | None = None,
        submit_on_focus_out: bool = False,
        input_type: str = "string",   # <--- NEW
        **entry_kwargs
    ):
        """
        label_text: label shown on the left
        on_change:  sync/async callback(value:str) fired on user edits
        on_submit:  sync/async callback(value:str) fired on Enter (and optionally on focus-out)
        info_text:  optional info string -> shows an InfoButton on the right
        submit_on_focus_out: if True, also fire on_submit when entry loses focus
        input_type: 'string' (default) or 'number' (restricts input to numbers)
        entry_kwargs: forwarded to ttk.Entry
        """
        super().__init__(master)
        self._on_change = on_change
        self._on_submit = on_submit
        self._submit_on_focus_out = submit_on_focus_out
        self._input_type = input_type.lower()
        self._suppress_change = False

        # --- layout ---
        self.pack(padx=10, pady=10, fill="x")

        # Label
        self._label = ttk.Label(self, text=label_text)
        self._label.pack(side="left", padx=(0, 8))

        # Entry
        self._var = tk.StringVar()
        vcmd = None
        if self._input_type == "number":
            vcmd = (self.register(self._validate_number), "%P")
            entry_kwargs["validate"] = "key"
            entry_kwargs["validatecommand"] = vcmd

        self._entry = ttk.Entry(self, textvariable=self._var, **entry_kwargs)
        self._entry.pack(side="left", fill="x", expand=True)

        # Bindings
        self._trace_id = self._var.trace_add("write", self._on_var_changed)
        self._entry.bind("<Return>", self._on_submit_event)
        if self._submit_on_focus_out:
            self._entry.bind("<FocusOut>", self._on_submit_event)

        # Info button
        if isinstance(info_text, str) and info_text.strip():
            title = f"{label_text} Explanation" if label_text else "Explanation"
            self._info_btn = InfoButton(self, title=title, message=info_text.strip())
            self._info_btn.pack(side="right", padx=(8, 0))
        else:
            self._info_btn = None

    # --- validation ---
    def _validate_number(self, proposed: str) -> bool:
        """Allow empty, '-', or valid float input."""
        if proposed == "" or proposed == "-" or proposed == ".":
            return True
        try:
            float(proposed)
            return True
        except ValueError:
            return False

    # --- public API ---
    def get_value(self) -> str | float | None:
        val = self._var.get()
        if self._input_type == "number":
            try:
                return float(val) if val not in ("", "-", ".") else None
            except ValueError:
                return None
        return val

    def set_value(self, value):
        self._suppress_change = True
        try:
            if self._input_type == "number" and value is not None:
                self._var.set(str(value))
            else:
                self._var.set("" if value is None else str(value))
        finally:
            self._suppress_change = False

    def focus(self):
        self._entry.focus_set()

    # --- events / callbacks ---
    def _on_var_changed(self, *_):
        if self._suppress_change:
            return
        if callable(self._on_change):
            self._fire(self._on_change, self.get_value())

    def _on_submit_event(self, _event=None):
        if callable(self._on_submit):
            self._fire(self._on_submit, self.get_value())

    # --- run sync or async safely ---
    def _fire(self, cb, value):
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


# --- Demo ----------------------------------------------------------------------
if __name__ == "__main__":
    async def on_change_async(v):
        print("change:", v)

    async def on_submit_async(v):
        print("submit:", v)

    root = tk.Tk()
    root.title("TextInput with type")

    # string input
    ti1 = TextInput(root, label_text="Name:", on_change=on_change_async, input_type="string", width=20)

    # number input
    ti2 = TextInput(root, label_text="Age:", on_submit=on_submit_async,
                    input_type="number", width=10, info_text="Enter your age as a number")

    root.mainloop()
