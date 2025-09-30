import tkinter as tk
from tkinter import ttk


class LogScreen(tk.Frame):
    def __init__(self, master, logs=None, **text_kwargs):
        """
        logs: list of strings to display
        text_kwargs: forwarded to tk.Text (e.g., font, height, width)
        """
        super().__init__(master)
        self.pack(padx=10, pady=10, fill="both", expand=True)

        # Text widget (read-only)
        text_kwargs.setdefault("wrap", "word")
        text_kwargs.setdefault("state", "disabled")
        text_kwargs.setdefault("font", ("Consolas", 10))

        self._text = tk.Text(self, **text_kwargs)
        self._text.pack(side="left", fill="both", expand=True)

        # Scrollbar
        sb = ttk.Scrollbar(self, orient="vertical", command=self._text.yview)
        sb.pack(side="right", fill="y")
        self._text.config(yscrollcommand=sb.set)

        # Load initial logs
        if logs:
            self.set_logs(logs)

    # --- API ---
    def set_logs(self, logs: list[str]):
        """Replace all logs."""
        self._text.config(state="normal")
        self._text.delete("1.0", tk.END)
        for line in logs:
            self._text.insert(tk.END, line + "\n")
        self._text.config(state="disabled")
        self._text.see(tk.END)

    def append_log(self, line: str):
        """Append a single log line at the end."""
        self._text.config(state="normal")
        self._text.insert(tk.END, line + "\n")
        self._text.config(state="disabled")
        self._text.see(tk.END)


# --- Demo ---
if __name__ == "__main__":
    import time

    root = tk.Tk()
    root.title("LogScreenWidget demo")

    logs = [
        "15:06:43 - INFO - Loaded 2 labels from models/coke_water_vision.pt",
        "15:06:44 - WARN - Low confidence detected",
        "15:06:44 - WARN - Low confidence detected",
        "15:06:44 - WARN - Low confidence detected",
        "15:06:44 - WARN - Low confidence detected",
        "15:06:44 - WARN - Low confidence detected",
        "15:06:44 - WARN - Low confidence detected",
    ]
    log_widget = LogScreen(root, logs=logs, height=10, width=80)

    # Simulate appending logs after 1 second
    def add_more():
        log_widget.append_log("15:06:45 - INFO - Processing frame...")
        root.after(1000, lambda: log_widget.append_log("15:06:46 - INFO - Done."))

    root.after(1000, add_more)

    root.mainloop()
