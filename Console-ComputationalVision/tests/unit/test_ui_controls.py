import tkinter as tk
from tkinter import ttk

import pytest

from shared.ui_controls import set_group_state, update_combobox_options


@pytest.fixture
def tk_root():
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tkinter display is unavailable")
    root.withdraw()
    yield root
    root.destroy()


def test_update_combobox_options_handles_empty_and_values(tk_root):
    variable = tk.StringVar(master=tk_root)
    combo = ttk.Combobox(tk_root, textvariable=variable)
    update_combobox_options(combo, variable, [], placeholder="Nothing")
    assert combo.cget("state") == "disabled"
    assert variable.get() == "Nothing"

    update_combobox_options(combo, variable, ["A", "B"], placeholder="Nothing")
    assert combo.cget("state") == "readonly"
    assert variable.get() == "A"


def test_set_group_state_toggles_buttons(tk_root):
    button1 = ttk.Button(tk_root, text="One")
    button2 = ttk.Button(tk_root, text="Two")
    set_group_state((button1, button2), enabled=False)
    assert button1.cget("state") == "disabled"
    assert button2.cget("state") == "disabled"
    set_group_state((button1, button2), enabled=True)
    assert button1.cget("state") == "normal"
    assert button2.cget("state") == "normal"
