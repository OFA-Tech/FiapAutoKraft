import tkinter as tk
import asyncio, threading, inspect, traceback


class ActionButton(tk.Button):
    def __init__(self, master, on_action, *,
                 text="Run", run_sync_in_thread=False,  # set True if your sync work is heavy
                 **kwargs):
        if not callable(on_action):
            raise TypeError("on_action must be callable (sync or async)")

        self._on_action = on_action
        self._run_sync_in_thread = bool(run_sync_in_thread)

        kwargs.setdefault("text", text)
        kwargs.setdefault("width", max(6, len(str(text))))
        kwargs.setdefault("anchor", "center")
        kwargs.setdefault("justify", "center")

        super().__init__(master, command=self._handle_click, **kwargs)
        self._design()

    # default layout like your other widgets
    def _design(self):
        self.pack(padx=10, pady=10)

    def _safe_enable(self):
        try:
            if self.winfo_exists():
                self.config(state="normal")
        except tk.TclError:
            pass

    def _handle_click(self):
        # disable immediately
        self.config(state="disabled")

        fn = self._on_action

        # 1) async function
        if inspect.iscoroutinefunction(fn):
            self._run_async(fn())
            return

        # 2) sync function (may return a coroutine)
        def run_sync():
            try:
                return fn()
            except Exception:
                traceback.print_exc()
                return None

        if self._run_sync_in_thread:
            # run sync work off the UI thread
            def worker():
                maybe = run_sync()
                if inspect.iscoroutine(maybe):
                    # if it yielded a coroutine, run it in this worker too
                    try:
                        asyncio.run(maybe)
                    except Exception:
                        traceback.print_exc()
                # back to Tk main thread
                try:
                    self.after(0, self._safe_enable)
                except tk.TclError:
                    pass
            threading.Thread(target=worker, daemon=True).start()
            return

        # run sync work on UI thread (will block until done)
        maybe = run_sync()
        if inspect.iscoroutine(maybe):
            self._run_async(maybe)
        else:
            self._safe_enable()

    def _run_async(self, coro):
        def worker():
            try:
                asyncio.run(coro)
            except Exception:
                traceback.print_exc()
            finally:
                try:
                    self.after(0, self._safe_enable)
                except tk.TclError:
                    pass
        threading.Thread(target=worker, daemon=True).start()


# --- Demo ---
if __name__ == "__main__":
    import time

    async def do_async():
        await asyncio.sleep(1.5)
        print("async action done")

    def do_sync():
        time.sleep(1)  # heavy sync (UI will freeze unless run_sync_in_thread=True)
        print("sync action done")

    root = tk.Tk()
    root.title("ActionButton demo")

    ActionButton(root, on_action=do_async, text="Async")
    ActionButton(root, on_action=do_sync, text="Sync (blocks)")
    ActionButton(root, on_action=do_sync, text="Sync (threaded)", run_sync_in_thread=True)

    root.mainloop()
