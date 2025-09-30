import tkinter as tk
from tkinter import ttk
import asyncio, threading, inspect, traceback

from widgets.InfoButton import InfoButton  # reusing your existing one


class ValueBar(tk.Frame):
    def __init__(self,
                 master,
                 min_value: float = 0.0,
                 max_value: float = 100.0,
                 default_value: float = 50.0,
                 decimals: int = 0,
                 label_text: str = "Volume:",
                 on_change=None,
                 info_text: str | None = None,
                 orient: str = "horizontal",
                 **scale_kwargs):
        """
        A labeled slider with decimal resolution and optional info modal.

        on_change: sync/async callback receiving the numeric value (rounded to `decimals`)
        orient: "horizontal" or "vertical"
        scale_kwargs: forwarded to tk.Scale (e.g., length=200)
        """
        super().__init__(master)
        self._on_change = on_change
        self._decimals = max(0, int(decimals))
        self._step = 10 ** (-self._decimals)

        # clamp default
        default_value = max(min_value, min(max_value, default_value))

        # --- default design
        self.pack(padx=10, pady=10, fill="x")

        # Left label
        self._label = ttk.Label(self, text=label_text)
        self._label.pack(side="left", padx=(0, 8))

        # Middle: the scale (tk.Scale supports 'resolution'; ttk.Scale does not)
        self._var = tk.DoubleVar(value=default_value)
        scale_kwargs.setdefault("from_", float(min_value))
        scale_kwargs.setdefault("to", float(max_value))
        scale_kwargs.setdefault("orient", tk.HORIZONTAL if orient == "horizontal" else tk.VERTICAL)
        scale_kwargs.setdefault("resolution", self._step)
        scale_kwargs.setdefault("showvalue", False)  # we show our own label

        self._scale = tk.Scale(self, variable=self._var, **scale_kwargs)
        self._scale.pack(side="left", fill="x", expand=True)

        # Right: live value label
        self._value_lbl = ttk.Label(self, width=max(4, self._decimals + 3))
        self._value_lbl.pack(side="left", padx=(8, 0))
        self._update_value_label(self._var.get())

        # Optional info button (far right)
        if isinstance(info_text, str) and info_text.strip():
            title = f"{label_text} Explanation" if label_text else "Explanation"
            self._info_btn = InfoButton(self, title=title, message=info_text.strip())
            self._info_btn.pack(side="right", padx=(8, 0))
        else:
            self._info_btn = None

        # Events: update while sliding and on release
        self._var.trace_add("write", self._on_var_changed)
        self._scale.bind("<ButtonRelease-1>", self._on_release)

    # --- public API ---
    def get_value(self) -> float:
        """Current value rounded to the configured decimals."""
        v = float(self._var.get())
        return round(v, self._decimals)

    def set_value(self, value: float):
        """Programmatically set the value (clamped), updates label, fires on_change once."""
        lo = float(self._scale.cget("from"))
        hi = float(self._scale.cget("to"))
        v = max(lo, min(hi, float(value)))
        self._var.set(v)  # triggers trace -> will update label + fire

    # --- internals ---
    def _update_value_label(self, v: float):
        self._value_lbl.config(text=f"{round(float(v), self._decimals):.{self._decimals}f}")

    def _on_var_changed(self, *_):
        v = self.get_value()
        self._update_value_label(v)
        self._fire_on_change(v)

    def _on_release(self, _event=None):
        # ensure final rounded value is sent after release too
        self._fire_on_change(self.get_value())

    def _fire_on_change(self, value: float):
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


# --- Demo ---
if __name__ == "__main__":
    async def on_change_async(v):
        # pretend to do async work
        await asyncio.sleep(0.05)
        print("value:", v)

    root = tk.Tk()
    root.title("ValueBar demo")

    vb1 = ValueBar(root,
                    min_value=0, max_value=1, default_value=0.25, decimals=2,
                    label_text="Gain:", on_change=on_change_async,
                    info_text="Adjust the gain between 0.00 and 1.00.",
                    length=260)

    vb2 = ValueBar(root,
                    min_value=-60, max_value=0, default_value=-12, decimals=1,
                    label_text="dB:", on_change=on_change_async,
                    length=260)

    root.mainloop()
