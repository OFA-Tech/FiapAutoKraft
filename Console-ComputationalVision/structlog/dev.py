"""Minimal :mod:`structlog.dev` helpers."""

from __future__ import annotations

from typing import Any, Dict


class ConsoleRenderer:
    def __call__(self, _logger: Any, _method: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
        return event_dict


__all__ = ["ConsoleRenderer"]
