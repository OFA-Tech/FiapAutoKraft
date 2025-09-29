from __future__ import annotations

import logging
import queue
import sys
import time


class TkQueueHandler(logging.Handler):
    def __init__(self, target_queue: "queue.Queue[str]") -> None:
        super().__init__()
        self.target_queue = target_queue

    def emit(self, record: logging.LogRecord) -> None:
        try:
            message = self.format(record)
        except Exception:
            self.handleError(record)
            return
        self.target_queue.put(message)


class QueueStreamRedirector:
    def __init__(self, target_queue: "queue.Queue[str]", label: str) -> None:
        self.target_queue = target_queue
        self.label = label
        self._buffer = ""

    def write(self, message: str) -> None:  # pragma: no cover
        if not message:
            return
        if not isinstance(message, str):
            message = str(message)
        normalised = message.replace("\r", "\n")
        if not normalised:
            return
        self._buffer += normalised
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            self._emit(line)

    def flush(self) -> None:  # pragma: no cover
        if self._buffer:
            self._emit(self._buffer)
            self._buffer = ""

    def close(self) -> None:  # pragma: no cover
        self.flush()

    def _emit(self, text: str) -> None:
        formatted = text.rstrip()
        if not formatted:
            return
        timestamp = time.strftime("%H:%M:%S")
        self.target_queue.put(f"{timestamp} - {self.label} - {formatted}")


def redirect_stdio(queue_handler: QueueStreamRedirector) -> tuple[object, object]:
    stdout = sys.stdout
    stderr = sys.stderr
    sys.stdout = queue_handler  # type: ignore[assignment]
    sys.stderr = queue_handler  # type: ignore[assignment]
    return stdout, stderr
