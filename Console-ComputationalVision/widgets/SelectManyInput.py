import tkinter as tk
from tkinter import ttk
import asyncio, threading, inspect, traceback

from widgets.InfoButton import InfoButton

class SelectManyInput(tk.Frame):
    def __init__(self, master, items=None, label_text="", on_change=None,
                 info_text: str | None = None, height=6, **list_kwargs):
        """
        items: list[(value, visual_name)]
        on_change: sync or async callback receiving List[value]
        info_text: if provided and non-empty, shows an InfoButton on the right
        height: visible rows in the listbox
        list_kwargs: forwarded to the Listbox (e.g., exportselection=0)
        """
        super().__init__(master)
        self._on_change = on_change
        self._values_to_names: dict = {}
        self._names_to_values: dict = {}
        self._suppress_events = False   # used when "disabled" fallback

        # --- default design like your other widgets
        self.pack(padx=10, pady=10, fill="x")

        # Left label
        self._label = ttk.Label(self, text=label_text)
        self._label.pack(side="left", padx=(0, 8))

        # Middle: a frame with listbox + scrollbar
        mid = ttk.Frame(self)
        mid.pack(side="left", fill="both", expand=True)

        self._list_var = tk.StringVar(value=[])
        list_kwargs.setdefault("selectmode", "extended")
        list_kwargs.setdefault("activestyle", "dotbox")
        # exportselection=0 prevents losing selection when focus leaves listbox (Windows)
        list_kwargs.setdefault("exportselection", 0)

        self._listbox = tk.Listbox(mid, listvariable=self._list_var, height=height, **list_kwargs)
        self._listbox.pack(side="left", fill="both", expand=True)

        sb = ttk.Scrollbar(mid, orient="vertical", command=self._listbox.yview)
        sb.pack(side="right", fill="y")
        self._listbox.config(yscrollcommand=sb.set)

        # Selection event
        self._listbox.bind("<<ListboxSelect>>", self._on_select_event)

        # Right: optional info button
        if isinstance(info_text, str) and info_text.strip():
            title = f"{label_text} Explanation" if label_text else "Explanation"
            self._info_btn = InfoButton(self, title=title, message=info_text.strip())
            self._info_btn.pack(side="right", padx=(8, 0))
        else:
            self._info_btn = None

        # Populate items
        self.set_items(items or [])

    # --- public API -------------------------------------------------------------
    def get_values(self) -> list:
        """Return list of selected underlying values."""
        names = self._get_selected_names()
        return [self._names_to_values[n] for n in names if n in self._names_to_values]

    def set_values(self, values: list):
        """Select multiple by underlying values."""
        name_set = {self._values_to_names[v] for v in values if v in self._values_to_names}
        self._select_names(name_set)
        self._fire_on_change(self.get_values())

    def set_items(self, items: list[tuple] | list):
        """Replace items with (value, visual_name). Handles empty/None (disabled)."""
        self._values_to_names.clear()
        self._names_to_values.clear()
        self._suppress_events = True  # avoid firing during rebuild
        try:
            if not items:
                self._list_var.set(["(no values available)"])
                self._set_disabled(True)
                return

            display_names = []
            for val, name in items:
                self._values_to_names[val] = name
                self._names_to_values[name] = val
                display_names.append(name)

            self._list_var.set(display_names)
            self._set_disabled(False)

            # default: select the first item and notify
            if display_names:
                self._listbox.selection_clear(0, "end")
                self._listbox.selection_set(0)
                self._listbox.see(0)
                self._fire_on_change(self.get_values())
        finally:
            self._suppress_events = False

    # --- internals --------------------------------------------------------------
    def _set_disabled(self, disabled: bool):
        """Disable/enable the listbox (with a safe fallback if state isn't supported)."""
        try:
            self._listbox.config(state=(tk.DISABLED if disabled else tk.NORMAL))
            self._suppress_events = disabled
        except tk.TclError:
            # Fallback for environments where Listbox 'state' isn't available
            self._suppress_events = disabled
            if disabled:
                self._listbox.unbind("<<ListboxSelect>>")
            else:
                self._listbox.bind("<<ListboxSelect>>", self._on_select_event)

    def _get_selected_names(self) -> list[str]:
        idxs = self._listbox.curselection()
        return [self._listbox.get(i) for i in idxs]

    def _select_names(self, names: set[str]):
        items = list(self._list_var.get())
        self._listbox.selection_clear(0, "end")
        for i, n in enumerate(items):
            if n in names:
                self._listbox.selection_set(i)
        if items:
            self._listbox.see(0)

    def _on_select_event(self, _event):
        if self._suppress_events:
            return
        self._fire_on_change(self.get_values())

    def _fire_on_change(self, values: list):
        cb = self._on_change
        if not callable(cb):
            return
        # async?
        if inspect.iscoroutinefunction(cb):
            self._run_async(cb(values)); return
        # sync (maybe returns coroutine)
        try:
            maybe = cb(values)
        except Exception:
            traceback.print_exc(); return
        if inspect.iscoroutine(maybe):
            self._run_async(maybe)

    def _run_async(self, coro):
        def worker():
            try: asyncio.run(coro)
            except Exception: traceback.print_exc()
        threading.Thread(target=worker, daemon=True).start()


if __name__ == "__main__":
    async def on_change_async(vals):
        await asyncio.sleep(0.3)
        print("selected values:", vals)

    root = tk.Tk()
    root.title("SelectManyInput demo")

    items = [
        ("pt", "Português"),
        ("en", "English"),
        ("es", "Español"),
        ("fr", "Français"),
        ("de", "Deutsch"),
    ]

    sm1 = SelectManyInput(
        root, items, label_text="Languages:",
        on_change=on_change_async,
        info_text="Pick one or more languages. Hold Ctrl/Cmd to multi-select.",
        height=5
    )

    sm2 = SelectManyInput(
        root, [], label_text="Empty list:",
        on_change=on_change_async,
        info_text="No options yet. Load data to enable this selection."
    )

    root.mainloop()