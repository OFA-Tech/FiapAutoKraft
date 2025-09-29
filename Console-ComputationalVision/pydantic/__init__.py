"""Minimal subset of :mod:`pydantic` used for configuration typing."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


def Field(default: Any = None, description: str | None = None) -> Any:
    return default


class BaseModel:
    """Placeholder base class mimicking the Pydantic API."""

    def model_dump(self) -> dict[str, Any]:  # pragma: no cover - unused helper
        return self.__dict__.copy()


__all__ = ["Field", "BaseModel"]
