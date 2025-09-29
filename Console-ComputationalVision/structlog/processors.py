"""Minimal processor implementations for local testing."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Dict


class TimeStamper:
    def __init__(self, fmt: str = "iso") -> None:
        self.fmt = fmt

    def __call__(self, _logger: Any, _method: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
        timestamp = datetime.utcnow()
        if self.fmt == "iso":
            event_dict["timestamp"] = timestamp.isoformat()
        else:  # pragma: no cover - fallback formatting
            event_dict["timestamp"] = timestamp.strftime(self.fmt)
        return event_dict


def add_log_level(_logger: Any, method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
    event_dict.setdefault("level", method_name)
    return event_dict


class StackInfoRenderer:
    def __call__(self, _logger: Any, _method: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
        return event_dict


class format_exc_info:  # pragma: no cover - placeholder hook
    def __call__(self, _logger: Any, _method: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
        return event_dict


__all__ = ["TimeStamper", "add_log_level", "StackInfoRenderer", "format_exc_info"]
