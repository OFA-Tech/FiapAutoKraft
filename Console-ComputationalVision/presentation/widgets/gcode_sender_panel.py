from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk

from application.gcode_connection import GcodeConnectionService
from application.poll_current_position import PollCurrentPositionUseCase
from application.send_coordinates import COMMAND_STATUS_TOPIC, GCODE_LOG_TOPIC, CommandDispatcher
from application.send_raw_command import SendRawCommandUseCase
from domain.motion.position import Feedrate, Position
from shared.bus import EventBus
from shared.logging_utils import append_with_limit
from shared.ui_controls import set_group_state, update_combobox_options
from shared.validation import ValidationError, ensure_positive_float, parse_float

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
        self._connected_port: str | None = None
        self._last_position: Position | None = None

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

        position_frame = ttk.Frame(self.frame)
        position_frame.grid(row=2, column=0, columnspan=3, sticky="ew", padx=4, pady=(4, 2))
        ttk.Label(position_frame, text="Current position").grid(row=0, column=0, sticky="w", padx=(0, 6))
        self.position_vars = {axis: tk.StringVar(value="-") for axis in ("x", "y", "z")}
        for idx, axis in enumerate(("x", "y", "z")):
            label_col = idx * 2 + 1
            entry_col = label_col + 1
            ttk.Label(position_frame, text=f"{axis.upper()}:").grid(row=0, column=label_col, sticky="w")
            entry = ttk.Entry(position_frame, textvariable=self.position_vars[axis], width=8, justify="right", state="readonly")
            entry.grid(row=0, column=entry_col, sticky="w", padx=(0, 6))

        coord_frame = ttk.LabelFrame(self.frame, text="Move")
        coord_frame.grid(row=3, column=0, columnspan=3, sticky="ew", padx=4, pady=(0, 4))
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

        self.feedrate_error_var = tk.StringVar(value="")
        ttk.Label(coord_frame, textvariable=self.feedrate_error_var, foreground="red").grid(
            row=row, column=0, columnspan=2, sticky="w"
        )
        row += 1

        action_bar = ttk.Frame(coord_frame)
        action_bar.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(4, 0))
        action_bar.columnconfigure(0, weight=1)
        action_bar.columnconfigure(1, weight=1)
        action_bar.columnconfigure(2, weight=1)
        self.move_button = ttk.Button(action_bar, text="Send", command=self._send_move, state="disabled")
        self.move_button.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        self.home_button = ttk.Button(action_bar, text="Home", command=self._home, state="disabled")
        self.home_button.grid(row=0, column=1, sticky="ew")
        self.command_status_var = tk.StringVar(value="")
        ttk.Label(action_bar, textvariable=self.command_status_var, foreground="gray").grid(
            row=0, column=2, sticky="w", padx=(6, 0)
        )

        command_frame = ttk.LabelFrame(self.frame, text="Raw command")
        command_frame.grid(row=4, column=0, columnspan=3, sticky="ew", padx=4, pady=(0, 4))
        command_frame.columnconfigure(0, weight=1)
        self.command_var = tk.StringVar()
        ttk.Entry(command_frame, textvariable=self.command_var).grid(row=0, column=0, sticky="ew", pady=2)
        self.command_button = ttk.Button(command_frame, text="Send", command=self._send_raw_command, state="disabled")
        self.command_button.grid(row=0, column=1, sticky="ew", padx=(4, 0))

        ttk.Label(self.frame, text="G-code Logs").grid(row=5, column=0, columnspan=3, sticky="w", padx=4)
        self.log_text = scrolledtext.ScrolledText(self.frame, height=8, state="disabled", wrap="word")
        self.log_text.grid(row=6, column=0, columnspan=3, sticky="nsew", padx=4, pady=(0, 4))

        self.status_var = tk.StringVar(value="Idle")
        ttk.Label(self.frame, textvariable=self.status_var).grid(row=7, column=0, columnspan=3, sticky="w", padx=4)

        self.refresh_ports()
        self._register_bus_handlers()

    def _register_bus_handlers(self) -> None:
        self._bus.subscribe(GCODE_LOG_TOPIC, self._on_log)
        self._bus.subscribe(COMMAND_STATUS_TOPIC, self._on_status)
        self._bus.subscribe(GCODE_INSTRUMENT_TOPIC, self._on_instrument)
        self._bus.subscribe(POSITION_TOPIC, self._on_position)

    def refresh_ports(self) -> None:
        ports = self._connection.list_ports()
        labels: list[str] = []
        self._ports_lookup = {}
        for port in ports:
            description = port.get("description") or port.get("manufacturer") or "Unknown"
            label = f"{port['device']} ({description})"
            labels.append(label)
            self._ports_lookup[label] = port
        if self._connected_port and self._connected_port not in (p.get("device") for p in ports):
            label = f"{self._connected_port} (connected)"
            labels.append(label)
            self._ports_lookup[label] = {"device": self._connected_port}
        update_combobox_options(
            self.serial_combo,
            self.serial_port_var,
            labels,
            placeholder="No ports available",
            preserve_selection=True,
        )
        if self._connected_port:
            for label in labels:
                info = self._ports_lookup.get(label, {})
                if info.get("device") == self._connected_port:
                    self.serial_port_var.set(label)
                    self.serial_combo.set(label)
                    break
        self._update_buttons()

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
        self._connected_port = info["device"]
        self.status_var.set(f"Connected to {info['device']}")
        self._on_log(f"Connected to {info['device']}")
        self._update_buttons()

    def _disconnect(self) -> None:
        if not self._connection.is_connected():
            return
        port = self._connected_port or self.serial_port_var.get()
        try:
            self._connection.disconnect()
        finally:
            self._connected_port = None
        self.status_var.set("Disconnected")
        if port:
            self._on_log(f"Disconnected from {port}")
        self._update_position_display(None)
        self._update_buttons()

    def _send_move(self) -> None:
        try:
            coords = {
                axis: parse_float(self.coord_vars[axis].get() or "0", axis.upper())
                for axis in ("x", "y", "z")
            }
        except ValidationError:
            messagebox.showerror("Invalid coordinates", "Enter numeric values for X, Y, Z")
            return
        try:
            feedrate = ensure_positive_float(self.feedrate_var.get() or "200", "Feedrate")
        except ValidationError as exc:
            message = "Feedrate must be positive" if "positive" in str(exc).lower() else "Enter a numeric feedrate"
            self.feedrate_error_var.set(message)
            return
        self.feedrate_error_var.set("")
        self._on_log(
            "Move command: X={x:.3f} Y={y:.3f} Z={z:.3f} F={f:.1f}".format(
                x=coords["x"], y=coords["y"], z=coords["z"], f=feedrate
            )
        )
        self._send_coordinates.execute(Position(**coords), Feedrate(feedrate))

    def _home(self) -> None:
        try:
            feedrate = ensure_positive_float(self.feedrate_var.get() or "200", "Feedrate")
        except ValidationError as exc:
            message = "Feedrate must be positive" if "positive" in str(exc).lower() else "Enter a numeric feedrate"
            self.feedrate_error_var.set(message)
            return
        self.feedrate_error_var.set("")
        self._on_log(f"Home command with F={feedrate:.1f}")
        self._home_machine.execute(Feedrate(feedrate))

    def _send_raw_command(self) -> None:
        command = self.command_var.get().strip()
        if not command:
            return
        self._on_log(f">> {command}")
        self._send_raw.execute(command, wait_for_ok=False)
        self.command_var.set("")

    def _on_log(self, message) -> None:
        if not isinstance(message, str):
            message = str(message)
        append_with_limit(self.log_text, message, 150)

    def append_log(self, message: str) -> None:
        self._on_log(message)

    def _on_status(self, status) -> None:
        if status == "Idle":
            self._busy = False
            self.command_status_var.set("")
        elif status == "refresh-position":
            self._poller.trigger()
            return
        else:
            self._busy = True
            self.command_status_var.set(str(status))
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

    def _on_position(self, event) -> None:
        position = getattr(event, "position", None)
        if isinstance(position, Position):
            self._last_position = position
        else:
            self._last_position = None
        self._update_position_display(self._last_position)
        self._update_buttons()

    def _update_buttons(self) -> None:
        connected = self._connection.is_connected()
        busy = self._busy or self._dispatcher.busy()
        state = "normal" if connected and not busy else "disabled"
        set_group_state((self.move_button, self.home_button, self.command_button), enabled=state == "normal")
        if connected:
            set_group_state((self.connect_button,), enabled=False)
            set_group_state((self.disconnect_button,), enabled=True)
        else:
            set_group_state((self.connect_button,), enabled=True)
            set_group_state((self.disconnect_button,), enabled=False)
        if not connected:
            self.command_status_var.set("")

    def _update_position_display(self, position: Position | None) -> None:
        if position is None:
            for var in self.position_vars.values():
                var.set("-")
            return
        self.position_vars["x"].set(f"{position.x:.3f}")
        self.position_vars["y"].set(f"{position.y:.3f}")
        self.position_vars["z"].set(f"{position.z:.3f}")

    def shutdown(self) -> None:
        if self._connection.is_connected():
            try:
                self._connection.disconnect()
            except Exception:
                pass
