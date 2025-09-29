import tkinter as tk

import pytest

from shared.logging_utils import append_with_limit


@pytest.fixture
def tk_root():
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tkinter display is unavailable")
    root.withdraw()
    yield root
    root.destroy()


def test_append_with_limit_prunes_fifo(tk_root):
    text = tk.Text(tk_root, state="disabled")
    for index in range(5):
        append_with_limit(text, f"line-{index}", max_lines=3)
    contents = text.get("1.0", "end-1c").splitlines()
    assert contents == ["line-2", "line-3", "line-4"]
    # Ensure widget remains read-only after operation
    assert text.cget("state") == "disabled"
