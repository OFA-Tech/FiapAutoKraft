from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk

from ...application.gcode_connection import GcodeConnectionService
from ...application.poll_current_position import PollCurrentPositionUseCase
from ...application.send_coordinates import COMMAND_STATUS_TOPIC, GCODE_LOG_TOPIC, CommandDispatcher
from ...application.send_raw_command import SendRawCommandUseCase
from ...domain.motion.position import Feedrate, Position
from ...shared.bus import EventBus

GCODE_INSTRUMENT_TOPIC = "gcode.instrument"
POSITION_TOPIC = "gcode.position"


class GcodeSenderPanel:
    def __init__(
        self,
        parent: tk.Widget,
        bus: EventBus,
        dispatcher: CommandDispatcher,
        connection: GcodeConnectionService,
        send_coordinates,
        home_machine,
        send_raw: SendRawCommandUseCase,
        poller: PollCurrentPositionUseCase,
    ) -> None:
        self.frame = ttk.LabelFrame(parent, text="G-code Sender")
        self.frame.columnconfigure(1, weight=1)
        self.frame.rowconfigure(6, weight=1)

        self._bus = bus
        self._dispatcher = dispatcher
        self._connection = connection
        self._send_coordinates = send_coordinates
        self._home_machine = home_machine
        self._send_raw = send_raw
        self._poller = poller

        self._ports_lookup: dict[str, dict] = {}
        self._busy = False
        self._connected = False

        self.serial_port_var = tk.StringVar()
        ttk.Label(self.frame, text="Serial port").grid(row=0, column=0, sticky="w", pady=2, padx=4)
        self.serial_combo = ttk.Combobox(self.frame, textvariable=self.serial_port_var, state="readonly")
        self.serial_combo.grid(row=0, column=1, sticky="ew", pady=2, padx=(0, 4))
        ttk.Button(self.frame, text="🔃", width=3, command=self.refresh_ports).grid(row=0, column=2, pady=2, padx=4)

        button_bar = ttk.Frame(self.frame)
        button_bar.grid(row=1, column=0, columnspan=3, sticky="ew", padx=4, pady=(0, 4))
        button_bar.columnconfigure(0, weight=1)
        button_bar.columnconfigure(1, weight=1)

        self.connect_button = ttk.Button(button_bar, text="Connect", command=self._connect)
        self.connect_button.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        self.disconnect_button = ttk.Button(button_bar, text="Disconnect", command=self._disconnect, state="disabled")
        self.disconnect_button.grid(row=0, column=1, sticky="ew")

        coord_frame = ttk.LabelFrame(self.frame, text="Move")
        coord_frame.grid(row=2, column=0, columnspan=3, sticky="ew", padx=4, pady=(0, 4))
        for col in range(4):
            coord_frame.columnconfigure(col, weight=1 if col == 1 else 0)

        self.coord_vars = {axis: tk.StringVar(value="0") for axis in ("x", "y", "z")}
        row = 0
        for axis in ("X", "Y", "Z"):
            ttk.Label(coord_frame, text=f"{axis}").grid(row=row, column=0, sticky="w", pady=2)
            ttk.Entry(coord_frame, textvariable=self.coord_vars[axis.lower()]).grid(row=row, column=1, sticky="ew", pady=2)
            row += 1

        ttk.Label(coord_frame, text="Feedrate").grid(row=row, column=0, sticky="w", pady=2)
        self.feedrate_var = tk.StringVar(value="200")
        ttk.Entry(coord_frame, textvariable=self.feedrate_var).grid(row=row, column=1, sticky="ew", pady=2)
        row += 1

        action_bar = ttk.Frame(coord_frame)
        action_bar.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(4, 0))
        action_bar.columnconfigure(0, weight=1)
        action_bar.columnconfigure(1, weight=1)
        self.move_button = ttk.Button(action_bar, text="Send", command=self._send_move, state="disabled")
        self.move_button.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        self.home_button = ttk.Button(action_bar, text="Home", command=self._home, state="disabled")
        self.home_button.grid(row=0, column=1, sticky="ew")

        command_frame = ttk.LabelFrame(self.frame, text="Raw command")
        command_frame.grid(row=3, column=0, columnspan=3, sticky="ew", padx=4, pady=(0, 4))
        command_frame.columnconfigure(0, weight=1)
        self.command_var = tk.StringVar()
        ttk.Entry(command_frame, textvariable=self.command_var).grid(row=0, column=0, sticky="ew", pady=2)
        self.command_button = ttk.Button(command_frame, text="Send", command=self._send_raw_command, state="disabled")
        self.command_button.grid(row=0, column=1, sticky="ew", padx=(4, 0))

        ttk.Label(self.frame, text="G-code Logs").grid(row=4, column=0, columnspan=3, sticky="w", padx=4)
        self.log_text = scrolledtext.ScrolledText(self.frame, height=8, state="disabled", wrap="word")
        self.log_text.grid(row=5, column=0, columnspan=3, sticky="nsew", padx=4, pady=(0, 4))

        self.status_var = tk.StringVar(value="Idle")
        ttk.Label(self.frame, textvariable=self.status_var).grid(row=6, column=0, columnspan=3, sticky="w", padx=4)

        self.refresh_ports()
        self._register_bus_handlers()

    def _register_bus_handlers(self) -> None:
        self._bus.subscribe(GCODE_LOG_TOPIC, self._on_log)
        self._bus.subscribe(COMMAND_STATUS_TOPIC, self._on_status)
        self._bus.subscribe(GCODE_INSTRUMENT_TOPIC, self._on_instrument)
        self._bus.subscribe(POSITION_TOPIC, lambda _event: self._update_buttons())

    def refresh_ports(self) -> None:
        ports = self._connection.list_ports()
        labels: list[str] = []
        self._ports_lookup = {}
        for port in ports:
            description = port.get("description") or port.get("manufacturer") or "Unknown"
            label = f"{port['device']} ({description})"
            labels.append(label)
            self._ports_lookup[label] = port
        if not labels:
            labels = ["No ports available"]
            self.serial_combo.configure(values=labels, state="disabled")
        else:
            self.serial_combo.configure(values=labels, state="readonly")
            self.serial_combo.set(labels[0])

    def _connect(self) -> None:
        label = self.serial_port_var.get()
        info = self._ports_lookup.get(label)
        if not info:
            messagebox.showerror("Serial port", "Select a valid serial port")
            return
        try:
            self._connection.connect(info["device"])
        except Exception as exc:
            messagebox.showerror("Connection failed", str(exc))
            return
        self._connected = True
        self.status_var.set(f"Connected to {info['device']}")
        self._update_buttons()

    def _disconnect(self) -> None:
        self._connection.disconnect()
        self._connected = False
        self.status_var.set("Disconnected")
        self._update_buttons()

    def _send_move(self) -> None:
        try:
            coords = {axis: float(self.coord_vars[axis].get() or "0") for axis in ("x", "y", "z")}
        except ValueError:
            messagebox.showerror("Invalid coordinates", "Enter numeric values for X, Y, Z")
            return
        try:
            feedrate = float(self.feedrate_var.get() or "200")
        except ValueError:
            messagebox.showerror("Invalid feedrate", "Enter a numeric feedrate")
            return
        if feedrate <= 0:
            messagebox.showerror("Invalid feedrate", "Feedrate must be positive")
            return
        self._send_coordinates.execute(Position(**coords), Feedrate(feedrate))

    def _home(self) -> None:
        try:
            feedrate = float(self.feedrate_var.get() or "200")
        except ValueError:
            messagebox.showerror("Invalid feedrate", "Enter a numeric feedrate")
            return
        if feedrate <= 0:
            messagebox.showerror("Invalid feedrate", "Feedrate must be positive")
            return
        self._home_machine.execute(Feedrate(feedrate))

    def _send_raw_command(self) -> None:
        command = self.command_var.get().strip()
        if not command:
            return
        self._send_raw.execute(command, wait_for_ok=False)
        self.command_var.set("")

    def _on_log(self, message) -> None:
        if not isinstance(message, str):
            message = str(message)
        self.log_text.configure(state="normal")
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state="disabled")

    def append_log(self, message: str) -> None:
        self._on_log(message)

    def _on_status(self, status) -> None:
        if status == "Idle":
            self._busy = False
        elif status == "refresh-position":
            self._poller.trigger()
            return
        else:
            self._busy = True
            self.status_var.set(status)
        self._update_buttons()

    def _on_instrument(self, payload) -> None:
        if isinstance(payload, tuple) and len(payload) == 2:
            name, data = payload
            formatted = self._format_event_payload(name, data)
        else:
            formatted = str(payload)
        self._on_log(formatted)

    def _format_event_payload(self, name: str, payload: dict) -> str:
        ordered = dict(payload)
        ordered.setdefault("event", name)
        parts: list[str] = []
        for key in ("timestamp", "thread", "command", "port", "ser_id", "status", "event"):
            if key in ordered:
                parts.append(f"{key}={ordered.pop(key)}")
        for key in sorted(ordered):
            parts.append(f"{key}={ordered[key]}")
        return "GRBL_EVENT " + " ".join(parts)

    def _update_buttons(self) -> None:
        connected = self._connection.is_connected()
        busy = self._busy or self._dispatcher.busy()
        state = "normal" if connected and not busy else "disabled"
        self.move_button.configure(state=state)
        self.home_button.configure(state=state)
        self.command_button.configure(state=state)
        self.connect_button.configure(state="disabled" if connected else "normal")
        self.disconnect_button.configure(state="normal" if connected else "disabled")
