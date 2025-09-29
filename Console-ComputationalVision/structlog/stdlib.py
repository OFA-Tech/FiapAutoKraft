"""Minimal stub of :mod:`structlog.stdlib` for local testing."""

from __future__ import annotations

import logging
from typing import Any


class BoundLogger:
    """Small logger wrapper capturing bound context values."""

    def __init__(self, logger: logging.Logger, **context: Any) -> None:
        self._logger = logger
        self._context = dict(context)

    def bind(self, **new_context: Any) -> "BoundLogger":
        context = {**self._context, **new_context}
        return self.__class__(self._logger, **context)

    def _emit(self, level: int, event: str, **kwargs: Any) -> None:
        payload = {**self._context, **kwargs}
        if payload:
            self._logger.log(level, "%s | %s", event, payload)
        else:
            self._logger.log(level, "%s", event)

    def info(self, event: str, **kwargs: Any) -> None:
        self._emit(logging.INFO, event, **kwargs)

    def warning(self, event: str, **kwargs: Any) -> None:  # pragma: no cover - passthrough
        self._emit(logging.WARNING, event, **kwargs)

    def error(self, event: str, **kwargs: Any) -> None:  # pragma: no cover - passthrough
        self._emit(logging.ERROR, event, **kwargs)


class LoggerFactory:
    """Factory returning stdlib loggers by name."""

    def __call__(self, name: str | None) -> logging.Logger:  # pragma: no cover - trivial
        return logging.getLogger(name)


__all__ = ["BoundLogger", "LoggerFactory"]
