# gui/MainPage.py
import tkinter as tk
from tkinter import ttk
import cv2

from gui.widgets.DropdownInput import DropdownInput
from gui.widgets.SelectManyInput import SelectManyInput
from gui.widgets.TextInput import TextInput
from gui.widgets.ActionButton import ActionButton
from gui.widgets.LogScreen import LogScreen
from gui.widgets.CameraPreview import CameraPreview
from gui.widgets.ValueBar import ValueBar
from gui.widgets.ValueBox import ValueBox


class MainPage(tk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.py_log = None
        self.pack(fill="both", expand=True)
        self._build_ui()

    def _tight_pack(self, widget, *, x=6, y=3, fill="x"):
        """Override the widget's default pack spacing (widgets auto-pack themselves)."""
        try:
            widget.pack_configure(padx=x, pady=y, fill=fill, expand=(fill == "both"))
        except tk.TclError:
            pass

    # --------------------------------------------------------------------- UI
    def _build_ui(self):
        # two columns
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)

        # ===================== LEFT COLUMN =====================
        left = ttk.Frame(self)
        left.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        left.columnconfigure(0, weight=1)

        # --- Camera & AI Settings ---
        cam_ai = ttk.LabelFrame(left, text="Camera and AI Settings", padding=(6, 4))
        cam_ai.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)
        cam_ai.columnconfigure(0, weight=1)

        # Model path
        self.inp_model = DropdownInput(
            cam_ai,
            items=[],
            label_text="Model path",
            on_change=lambda v: None,
            info_text="Select a model for the AI to use"
        )
        self._tight_pack(self.inp_model)

        # Camera
        camera_opts = [("0", "0: Camera 0 - MSMF (640x480)"),
                       ("1", "1: Camera 1 - MSMF (640x480)")]
        self.dd_camera = DropdownInput(
            cam_ai, camera_opts, label_text="Camera",
            on_change=self._on_camera_changed,
            info_text="Select a directshow camera device",
            width=36,
            refresh_function=self._refresh_cameras
        )
        self._tight_pack(self.dd_camera)

        # Target FPS
        self.dd_fps = DropdownInput(
            cam_ai,
            items=[("15", "15"), ("30", "30"), ("60", "60")],
            label_text="Target FPS",
            on_change=lambda v: None,
            info_text="UI refresh target; preview thread adapts accordingly",
            width=12
        )
        self._tight_pack(self.dd_fps)

        # Inference interval (number)
        self.inp_interval = TextInput(
            cam_ai,
            label_text="Inference interval:",
            on_submit=lambda v: None,
            info_text="Run detection every N frames",
            input_type="number",
            width=12
        )
        self.inp_interval.set_value(3)
        self._tight_pack(self.inp_interval)

        # Confidence threshold (slider)
        self.inp_conf = ValueBar(
            cam_ai,
            min_value=0, max_value=1, default_value=0.6, decimals=2,
            label_text="Confidence threshold:",
            info_text="Minimum confidence [0..1] to draw/emit",
            orient="horizontal",
            on_change=lambda v: None,
        )
        self._tight_pack(self.inp_conf, fill="x")

        # Device
        self.dd_device = DropdownInput(
            cam_ai,
            items=[("auto", "auto"), ("cpu", "cpu"), ("cuda", "cuda")],
            label_text="Device",
            on_change=lambda v: None,
            info_text="Inference device selection",
            width=16
        )
        self._tight_pack(self.dd_device)

        # Start/Stop row (tighter padding)
        self.state_var = "Idle"
        row = ttk.Frame(cam_ai)
        row.pack(fill="x", padx=6, pady=4)
        state_info = ValueBox(row, title= "State:", value=self.state_var)
        state_info.pack_configure(side="left", padx=6, expand=True)
        current_x = ValueBox(row, title="Current X:", value=0)
        current_x.pack_configure(side="left", padx=6, expand=True)
        current_y = ValueBox(row, title="Current Y:", value=0)
        current_y.pack_configure(side="left", padx=6, expand=True)
        current_z = ValueBox(row, title="Current Z:", value=0)
        current_z.pack_configure(side="left", padx=6, expand=True)
        btn_stop = ActionButton(row, text="Stop", on_action=self._on_stop_clicked)
        btn_stop.pack_configure(side="right", padx=6, expand=True)  # put next to it
        btn_start = ActionButton(row, text="Start", on_action=self._on_start_clicked)
        btn_start.pack_configure(side="right", padx=6, expand=True)  # override the auto-pack


        # Label filters
        filters = ttk.LabelFrame(left, text="Label filters", padding=(6, 4))
        filters.grid(row=1, column=0, sticky="nsew", padx=4, pady=6)
        filters.columnconfigure(0, weight=1)

        btns = ttk.Frame(filters); btns.pack(fill="x", padx=6, pady=(4, 2))
        ttk.Button(btns, text="Select all", command=self._label_select_all).pack(side="left")
        ttk.Label(btns, text="").pack(side="left", expand=True)
        ttk.Button(btns, text="Clear", command=self._label_clear).pack(side="left")

        self.sel_labels = SelectManyInput(
            filters,
            items=[("agua", "agua"), ("coke", "coke")],
            label_text="",
            on_change=self._on_labels_changed,
            height=6
        )
        self._tight_pack(self.sel_labels, fill="both")

        # --- G-code Sender ---
        gcode = ttk.LabelFrame(left, text="G-code Sender", padding=(6, 4))
        gcode.grid(row=2, column=0, sticky="nsew", padx=4, pady=4)
        gcode.columnconfigure(0, weight=1)

        self.dd_serial = DropdownInput(
            gcode,
            items=[("COM3", "COM3 (Standard Serial over Bluetooth link (COM3))")],
            label_text="Serial port",
            on_change=lambda v: None,
            info_text="Pick the serial port connected to the controller",
            width=44
        )
        self._tight_pack(self.dd_serial)

        row2 = ttk.Frame(gcode); row2.pack(fill="x", padx=6, pady=2)
        btn_connect =ActionButton(row2, text="Connect", on_action=self._on_connect)
        btn_connect.pack_configure(side="left", padx=6, expand=True)
        btn_disconnect = ActionButton(row2, text="Disconnect", on_action=self._on_disconnect)
        btn_disconnect.pack_configure(side="left", padx=6, expand=True)

        pos = ttk.Frame(gcode); pos.pack(fill="x", padx=6, pady=4)
        self.inp_x = TextInput(pos, label_text="X:", width=6, input_type="number")
        self.inp_x.pack_configure(side="left", padx=6, expand=True)
        self.inp_y = TextInput(pos, label_text="Y:", width=6, input_type="number")
        self.inp_y.pack_configure(side="left", padx=6, expand=True)
        self.inp_z = TextInput(pos, label_text="Z:", width=6, input_type="number")
        self.inp_z.pack_configure(side="left", padx=6, expand=True)
        self.inp_feed = TextInput(pos, label_text="Feedrate:", width=8, input_type="number")
        self.inp_feed.pack_configure(side="left", padx=6, expand=True)
        send_gcode = ActionButton(pos, text="Send", on_action=self._on_send_move)
        send_gcode.pack_configure(side="left", padx=6, expand=True)
        center_core = ActionButton(pos, text="Center-It", on_action=self._on_home)
        center_core.pack_configure(side="left", padx=6, expand=True)

        line = ttk.Frame(gcode); line.pack(fill="x", padx=6, pady=(2, 6))
        self.inp_gline = TextInput(line, label_text="Raw G-Code", on_submit=self._on_send_line, width=48); self._tight_pack(self.inp_gline)
        ActionButton(line, text="Send", on_action=self._on_send_line)

        # give left sections stretch
        left.rowconfigure(3, weight=1)

        # ===================== RIGHT COLUMN =====================
        right = ttk.Frame(self)
        right.grid(row=0, column=1, sticky="nsew", padx=8, pady=8)
        right.columnconfigure(0, weight=1)
        right.rowconfigure(0, weight=1)

        # Camera Preview group
        preview_group = ttk.LabelFrame(right, text="Camera Preview", padding=(6, 4))
        preview_group.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)
        preview_group.columnconfigure(0, weight=1)
        preview_group.rowconfigure(0, weight=1)

        # Holder to center the preview
        holder = ttk.Frame(preview_group)
        holder.grid(row=0, column=0, sticky="n")  # top-center
        holder.columnconfigure(0, weight=1)

        self.cap = None
        self.preview = CameraPreview(holder, width=640, height=360, fps=30,
                                     capture=self.cap)
        # Stop it from filling; center it
        try:
            self.preview.pack_configure(padx=0, pady=0, fill=None, expand=False)
        except tk.TclError:
            pass

        # Gcode|Python Logs group
        pylog_group = ttk.LabelFrame(right, text="G-code | Python Logs", padding=(6, 4))
        pylog_group.grid(row=1, column=0, sticky="nsew", padx=4, pady=(6, 0))
        LogScreen(pylog_group, logs=[
            "16:16:30 - INFO - Loaded 2 labels from",
            r"C:\Dev\OFA-Tech\FiapAutoKraft\Console-ComputationalVision\models\coke_water_vision.pt"
        ], height=10, width=80)
        LogScreen(pylog_group, logs=[], height=10, width=80)

        right.rowconfigure(1, weight=1)

    # ----------------------------------------------------- Callbacks (stubs)
    def _on_model_submit(self, value):
        self.py_log.append_log(f"Model set: {value}")

    async def _refresh_cameras(self):
        # Dummy implementation; replace with actual camera detection logic
        camera_opts = [("0", "0: Camera 0 - MSMF (640x480)"),
                       ("1", "1: Camera 1 - MSMF (640x480)")]
        self.dd_camera.set_items(camera_opts)
        self.py_log.append_log("Camera list refreshed")



    def _on_camera_changed(self, cam_value):
        try:
            if self.cap:
                self.cap.release()
        except Exception:
            pass
        self.cap = None
        if cam_value is not None:
            try:
                idx = int(cam_value)
                cap = cv2.VideoCapture(idx)
                if cap.isOpened():
                    self.cap = cap
                    self.preview.set_capture(self.cap)
                    self.preview.start()
                else:
                    cap.release()
                    self.preview.set_capture(None)
            except Exception:
                self.preview.set_capture(None)

    def _on_start_clicked(self):
        self.state_var.set("Running")
        self.py_log.append_log("Start clicked")

    def _on_stop_clicked(self):
        self.state_var.set("Idle")
        self.py_log.append_log("Stop clicked")
        self.preview.stop()

    def _label_select_all(self):
        names = [n for n in self.sel_labels._list_var.get()]
        values = []
        for n in names:
            v = self.sel_labels._names_to_values.get(n)
            if v is not None:
                values.append(v)
        self.sel_labels.set_values(values)

    def _label_clear(self):
        self.sel_labels.set_values([])

    def _on_labels_changed(self, values):
        self.py_log.append_log(f"Label filter changed: {values}")

    def _on_connect(self):
        self.gcode_log.append_log("Connect clicked")

    def _on_disconnect(self):
        self.gcode_log.append_log("Disconnect clicked")

    def _on_send_move(self):
        x = self.inp_x.get_value()
        y = self.inp_y.get_value()
        z = self.inp_z.get_value()
        f = self.inp_feed.get_value()
        self.gcode_log.append_log(f"Move -> X:{x} Y:{y} Z:{z} F:{f}")

    def _on_home(self):
        self.gcode_log.append_log("Home sent")

    def _on_send_line(self, *_):
        line = self.inp_gline.get_value()
        if line:
            self.gcode_log.append_log(f"> {line}")


# --------------------------- Standalone run ---------------------------
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Console Computational Vision")
    root.geometry("1280x720")
    root.rowconfigure(0, weight=1)
    root.columnconfigure(0, weight=1)
    MainPage(root)
    root.mainloop()
