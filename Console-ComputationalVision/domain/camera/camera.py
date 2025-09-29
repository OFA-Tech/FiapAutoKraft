from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Resolution:
    width: int
    height: int

    def as_tuple(self) -> tuple[int, int]:
        return self.width, self.height


@dataclass(frozen=True)
class Camera:
    identifier: str
    index: int
    name: str
    backend: Optional[str] = None
    default_resolution: Optional[Resolution] = None


@dataclass(frozen=True)
class Frame:
    data: "np.ndarray"
    timestamp: float

    @property
    def shape(self) -> tuple[int, ...]:
        return self.data.shape


try:
    import numpy as np  # type: ignore
except Exception:  # pragma: no cover - numpy missing in minimal envs
    np = None  # type: ignore
