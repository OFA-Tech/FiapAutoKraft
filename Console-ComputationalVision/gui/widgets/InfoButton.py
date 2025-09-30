import tkinter as tk
from tkinter import ttk
import traceback

class InfoModal(tk.Toplevel):
    def __init__(self, master, title: str, message: str, *, width=420, wrap=380):
        super().__init__(master)
        self.title(title)
        self.resizable(False, False)

        # Keep above parent & center-ish
        self.transient(master)
        self.configure(padx=14, pady=12)

        # --- Content ---
        header = ttk.Label(self, text=title, font=("TkDefaultFont", 10, "bold"))
        header.pack(anchor="w", pady=(0, 6))

        body = ttk.Label(self, text=message, wraplength=wrap, justify="left")
        body.pack(anchor="w")

        btn_row = ttk.Frame(self)
        btn_row.pack(fill="x", pady=(12, 0))
        btn_ok = ttk.Button(btn_row, text="OK", command=self._ok)
        btn_ok.pack(side="right")

        # keyboard / close
        self.bind("<Return>", lambda e: self._ok())
        self.bind("<Escape>", lambda e: self._ok())
        self.protocol("WM_DELETE_WINDOW", self._ok)

        # Place near parent center
        self.update_idletasks()
        try:
            px = master.winfo_rootx() + (master.winfo_width() // 2) - (self.winfo_width() // 2)
            py = master.winfo_rooty() + (master.winfo_height() // 2) - (self.winfo_height() // 2)
            self.geometry(f"+{max(0, px)}+{max(0, py)}")
        except Exception:
            traceback.print_exc()

        # True modal behavior
        self.grab_set()
        self.focus_set()

    def _ok(self):
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()


class InfoButton(tk.Button):
    def __init__(self, master, *, title="Info", message="This is an info dialog.", **kwargs):
        # default look & behavior
        kwargs.setdefault("text", "?")
        kwargs.setdefault("width", 2)  # give some room so it looks like a square button
        kwargs.setdefault("anchor", "center")  # center the text/icon horizontally
        kwargs.setdefault("justify", "center")
        kwargs.setdefault("compound", "center")
        super().__init__(master, command=self._handle_click, **kwargs)
        self._info_title = title
        self._info_message = message
        self._design()

    def _design(self):
        # simple default layout like your other widgets
        self.pack(padx=10, pady=10)

    def _handle_click(self):
        # Open modal and block until closed (modal manages its own grab/wait)
        try:
            dlg = InfoModal(self.master, self._info_title, self._info_message)
            self.wait_window(dlg)  # block only this handler, UI stays responsive
        except tk.TclError:
            # Parent might be gone; ignore
            pass


# Demo
if __name__ == "__main__":
    root = tk.Tk()
    root.title("InfoButton demo")

    # Example: explain what a refresh button (or any feature) does
    info_text = (
        "This button refreshes the device list.\n\n"
        "• Re-queries serial ports\n"
        "• Rescans cameras\n"
        "• Reloads AI models from disk\n\n"
        "Use it when you plug a new device or add a new model file."
    )

    info_btn = InfoButton(root, title="What does Refresh do?", message=info_text)

    # You can create multiple with different messages:
    InfoButton(root, title="About Models", message="Models are loaded from the 'models/' folder.").pack()

    root.mainloop()
