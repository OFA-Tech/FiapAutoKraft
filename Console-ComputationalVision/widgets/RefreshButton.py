import tkinter as tk
import asyncio
import threading
import inspect
import traceback

class RefreshButton(tk.Button):
    def __init__(self, master, on_refresh, **kwargs):
        if not callable(on_refresh):
            raise TypeError("on_refresh must be callable (sync or async)")
        self._on_refresh = on_refresh
        kwargs.setdefault("text", "🔃")
        kwargs.setdefault("anchor", "center")  # center the text/icon horizontally
        kwargs.setdefault("justify", "center")
        kwargs.setdefault("compound", "center")
        super().__init__(master, command=self._handle_click, **kwargs)
        self._design()

    def _design(self):
        self.pack(padx=10, pady=10)

    def _safe_enable(self):
        try:
            if self.winfo_exists():
                self.config(state="normal")
        except tk.TclError:
            pass  # widget/root already destroyed

    def _handle_click(self):
        self.config(state="disabled")

        # Async handler?
        if inspect.iscoroutinefunction(self._on_refresh):
            self._run_async(self._on_refresh())
            return

        # Sync handler that *returns* a coroutine?
        try:
            maybe = self._on_refresh()
        except Exception:
            traceback.print_exc()
            self._safe_enable()
            return

        if inspect.iscoroutine(maybe):
            self._run_async(maybe)
        else:
            self._safe_enable()

    def _run_async(self, coro):
        def worker():
            try:
                asyncio.run(self._await_and_finalize(coro))
            except Exception:
                traceback.print_exc()
                # schedule safe UI re-enable even if the task failed
                try:
                    self.after(0, self._safe_enable)
                except tk.TclError:
                    pass

        threading.Thread(target=worker, daemon=True).start()

    async def _await_and_finalize(self, coro):
        try:
            await coro
        finally:
            # hop back to Tk main thread safely
            try:
                self.after(0, self._safe_enable)
            except tk.TclError:
                pass


if __name__ == "__main__":
    import time

    async def async_refresh():
        # simulate I/O
        await asyncio.sleep(2)
        print("async refresh done")

    def sync_refresh():
        time.sleep(1)
        print("sync refresh done")

    root = tk.Tk()
    btn1 = RefreshButton(root, on_refresh=async_refresh)

    btn2 = RefreshButton(root, on_refresh=sync_refresh, text="Sync Refresh")

    root.mainloop()
