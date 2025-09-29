"""Scheduling helpers for background worker loops."""

from __future__ import annotations

import time


class IntervalScheduler:
    """Track monotonic deadlines for periodic tasks."""

    def __init__(self, interval: float) -> None:
        self.interval = interval
        self._next_deadline = time.monotonic()

    def timeout(self) -> float:
        """Return the time remaining until the next deadline."""

        return max(0.0, self._next_deadline - time.monotonic())

    def defer(self) -> None:
        """Skip the current tick and reschedule for ``interval`` seconds later."""

        self._next_deadline = time.monotonic() + self.interval

    def executed(self) -> None:
        """Record that the job has run and compute the next deadline."""

        self._next_deadline = time.monotonic() + self.interval

    def skip_if(self, condition: bool) -> bool:
        """Skip the tick if ``condition`` holds, returning ``True`` if skipped."""

        if condition:
            self.defer()
            return True
        return False
