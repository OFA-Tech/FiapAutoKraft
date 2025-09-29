from __future__ import annotations

from domain.motion.gcode_sender import GcodeSender
from .send_coordinates import CommandDispatcher, CommandRequest


class SendRawCommandUseCase:
    def __init__(self, dispatcher: CommandDispatcher, sender: GcodeSender) -> None:
        self._dispatcher = dispatcher
        self._sender = sender

    def execute(self, command: str, wait_for_ok: bool = False) -> None:
        command = command.strip()
        if not command:
            return

        def _run():
            return self._sender.send_raw(command, wait_for_ok=wait_for_ok)

        self._dispatcher.dispatch(
            CommandRequest(
                name=f"RAW {command}",
                execute=_run,
                status_text=f"Sending {command}",
                refresh_position=True,
            )
        )
