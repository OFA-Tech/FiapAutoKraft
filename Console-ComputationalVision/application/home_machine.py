from __future__ import annotations

from domain.motion.gcode_sender import GcodeSender
from domain.motion.position import Feedrate

from .send_coordinates import CommandDispatcher, CommandRequest


class HomeMachineUseCase:
    def __init__(self, dispatcher: CommandDispatcher, sender: GcodeSender) -> None:
        self._dispatcher = dispatcher
        self._sender = sender

    def execute(self, feedrate: Feedrate) -> None:
        def _run():
            return self._sender.home(feedrate)

        self._dispatcher.dispatch(
            CommandRequest(
                name="Home",
                execute=_run,
                status_text="Homing…",
                refresh_position=True,
            )
        )
