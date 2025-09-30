"""Integration utilities between the vision detections and the G-code sender."""

from __future__ import annotations

import asyncio
import logging
import math
import threading
from typing import Any, Callable, Coroutine, Iterable, Optional, Sequence, Tuple

from services.GCodeSender import GCodeSender

RunAsyncCallable = Callable[[Coroutine[Any, Any, Any], Optional[str]], None]
LogCallback = Callable[[str], None]


class VisionToGCodeIntegrator:
    """Convert AI detections into G-code moves."""

    def __init__(
        self,
        gcode_sender: GCodeSender,
        run_async: RunAsyncCallable,
        log_python: Optional[LogCallback] = None,
        log_gcode: Optional[LogCallback] = None,
    ) -> None:
        self._gcode_sender = gcode_sender
        self._run_async = run_async
        self._log_python = log_python or (lambda message: None)
        self._log_gcode = log_gcode or (lambda message: None)
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._lock = threading.Lock()
        self._last_command: Optional[Tuple[float, float]] = None

    def reset(self) -> None:
        """Forget previously issued commands."""

        with self._lock:
            self._last_command = None

    def handle_detections(
        self,
        detections: Sequence[dict],
        frame_size: Tuple[int, int],
    ) -> None:
        """Pick the highest-confidence detection and move the tool head."""

        if not detections:
            return

        best = max(detections, key=lambda item: float(item.get("conf", 0.0)))
        center = best.get("center_xy")
        if not isinstance(center, Iterable):
            self._logger.debug("Skipping detection without a valid center: %s", best)
            return

        try:
            cx, cy = map(float, center)
        except (TypeError, ValueError):
            self._logger.debug("Skipping detection with malformed center: %s", center)
            return

        width, height = frame_size
        if width <= 1 or height <= 1:
            self._logger.debug("Invalid frame size provided: %s", frame_size)
            return

        x_coord, y_coord = self._convert_pixel_to_machine(cx, cy, width, height)

        with self._lock:
            if self._last_command and self._is_close(self._last_command, (x_coord, y_coord)):
                return
            self._last_command = (x_coord, y_coord)

        if not self._gcode_connected():
            self._log_gcode("AI detection available but G-code sender is not connected.")
            return

        move_coro = self._invoke_move(x_coord, y_coord)
        if move_coro is None:
            # The move executed synchronously; still log for visibility.
            self._log_gcode(
                f"AI move executed synchronously to X:{x_coord:.3f} Y:{y_coord:.3f}"
            )
            return

        message = (
            f"AI target '{best.get('label', 'unknown')}' at conf {best.get('conf', 0.0):.2f} "
            f"-> Move to X:{x_coord:.3f} Y:{y_coord:.3f}"
        )
        self._run_async(move_coro, success_message=message)

    def _invoke_move(self, x_coord: float, y_coord: float) -> Optional[Coroutine[Any, Any, Any]]:
        """Call ``move_xy`` if available, otherwise fall back to specific coordinates."""

        move_func = getattr(self._gcode_sender, "move_xy", None)
        if callable(move_func):
            result = move_func(x_coord, y_coord)
            if asyncio.iscoroutine(result):
                return result
            return None

        self._log_python(
            "GCodeSender.move_xy is unavailable; falling back to set_specific_coordinates."
        )
        fallback = getattr(self._gcode_sender, "set_specific_coordinates", None)
        if callable(fallback):
            return fallback(x_coord, y_coord)
        raise AttributeError("GCodeSender lacks both move_xy and set_specific_coordinates methods")

    def _gcode_connected(self) -> bool:
        nano = getattr(self._gcode_sender, "nano", None)
        return bool(nano and getattr(nano, "is_open", False))

    @staticmethod
    def _convert_pixel_to_machine(
        cx: float,
        cy: float,
        width: int,
        height: int,
    ) -> Tuple[float, float]:
        """Map pixel coordinates to machine coordinates within [-5, 5]."""

        width_range = max(1, width - 1)
        height_range = max(1, height - 1)

        x = (cx / width_range) * 10.0 - 5.0
        y = 5.0 - (cy / height_range) * 10.0

        x = max(-5.0, min(5.0, x))
        y = max(-5.0, min(5.0, y))
        return x, y

    @staticmethod
    def _is_close(
        previous: Tuple[float, float],
        current: Tuple[float, float],
        *,
        tolerance: float = 0.05,
    ) -> bool:
        return math.isclose(previous[0], current[0], abs_tol=tolerance) and math.isclose(
            previous[1], current[1], abs_tol=tolerance
        )
