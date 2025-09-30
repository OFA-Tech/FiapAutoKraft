import tkinter as tk

class GuiServices:
    def __init__(self, root):
        self.root = root
        self.root.title("GUI Services Example")
        self.label = tk.Label(root, text="Hello, World!")
        self.label.pack(pady=20)
        self.button = tk.Button(root, text="Click Me", command=self.on_button_click)
        self.button.pack(pady=10)

    def on_button_click(self):
        self.label.config(text="Button Clicked!")