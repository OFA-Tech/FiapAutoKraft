from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Position:
    x: float
    y: float
    z: float


@dataclass(frozen=True)
class Feedrate:
    value: float

    def __post_init__(self) -> None:
        if self.value <= 0:
            raise ValueError("Feedrate must be positive")
