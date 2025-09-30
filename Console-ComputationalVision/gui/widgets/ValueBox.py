import tkinter as tk
from tkinter import font


class ValueBox(tk.Frame):
    def __init__(self, master, title: str, value: str | float,
                 border_color: str = "#4a90e2", width=150, height=80, **kwargs):
        """
        A card-like box with title + value and a colored border.

        title: str, small label text
        value: str|float, big number/text
        border_color: hex color string
        width/height: size of the box
        """
        super().__init__(master, **kwargs)

        self._title = str(title)
        self._value = str(value)
        self._border_color = border_color
        self._width = width
        self._height = height

        # canvas to simulate rounded border
        self._canvas = tk.Canvas(self, width=width, height=height,
                                 highlightthickness=0, bg=self.cget("bg"))
        self._canvas.pack(fill="both", expand=True)

        # draw rounded rectangle
        self._draw_box()

        # fonts
        self._title_font = font.Font(size=10, weight="normal")
        self._value_font = font.Font(size=16, weight="bold")

        # add text
        self._title_id = self._canvas.create_text(width//2, 20, text=self._title,
                                                  font=self._title_font, fill="black")
        self._value_id = self._canvas.create_text(width//2, height//2+15,
                                                  text=self._value,
                                                  font=self._value_font, fill="black")

    def _draw_box(self):
        r = 15  # border radius
        x0, y0, x1, y1 = 2, 2, self._width-2, self._height-2

        self._canvas.create_arc(x0, y0, x0+r*2, y0+r*2, start=90, extent=90, outline=self._border_color, style="arc", width=2)
        self._canvas.create_arc(x1-r*2, y0, x1, y0+r*2, start=0, extent=90, outline=self._border_color, style="arc", width=2)
        self._canvas.create_arc(x0, y1-r*2, x0+r*2, y1, start=180, extent=90, outline=self._border_color, style="arc", width=2)
        self._canvas.create_arc(x1-r*2, y1-r*2, x1, y1, start=270, extent=90, outline=self._border_color, style="arc", width=2)

        # sides
        self._canvas.create_line(x0+r, y0, x1-r, y0, fill=self._border_color, width=2)
        self._canvas.create_line(x0+r, y1, x1-r, y1, fill=self._border_color, width=2)
        self._canvas.create_line(x0, y0+r, x0, y1-r, fill=self._border_color, width=2)
        self._canvas.create_line(x1, y0+r, x1, y1-r, fill=self._border_color, width=2)

    # --- public API ---
    def set_value(self, value: str | float):
        self._value = str(value)
        self._canvas.itemconfig(self._value_id, text=self._value)

    def set_title(self, title: str):
        self._title = str(title)
        self._canvas.itemconfig(self._title_id, text=self._title)

    def set_border_color(self, color: str):
        self._border_color = color
        self._canvas.delete("all")
        self._draw_box()
        # redraw texts
        self._title_id = self._canvas.create_text(self._width//2, 20, text=self._title,
                                                  font=self._title_font, fill="black")
        self._value_id = self._canvas.create_text(self._width//2, self._height//2+15,
                                                  text=self._value,
                                                  font=self._value_font, fill="black")


# --- Demo ---
if __name__ == "__main__":
    root = tk.Tk()
    root.title("ValueBox demo")

    vb1 = ValueBox(root, "Temperature", "23°C", border_color="#e74c3c")
    vb1.pack(padx=10, pady=10)

    vb2 = ValueBox(root, "Accuracy", "98.5%", border_color="#2ecc71")
    vb2.pack(padx=10, pady=10)

    # dynamically update value
    def update():
        vb1.set_value("24°C")
        vb1.set_border_color("#3498db")
    root.after(2000, update)

    root.mainloop()
