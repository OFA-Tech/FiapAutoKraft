"""Very small subset of the :mod:`structlog` API required for tests."""

from __future__ import annotations

import logging
from typing import Any, Callable, Iterable

from . import dev, processors, stdlib

_LOGGER_FACTORY: Callable[[str | None], logging.Logger] = logging.getLogger
_WRAPPER_CLASS = stdlib.BoundLogger
_PROCESSORS: Iterable[Callable[[Any, str, dict[str, Any]], dict[str, Any]]] = []


def configure(
    *,
    processors: Iterable[Callable[[Any, str, dict[str, Any]], dict[str, Any]]] | None = None,
    wrapper_class: type[stdlib.BoundLogger] | None = None,
    logger_factory: Callable[[str | None], logging.Logger] | None = None,
    cache_logger_on_first_use: bool = True,
) -> None:
    global _LOGGER_FACTORY, _WRAPPER_CLASS, _PROCESSORS
    if processors is not None:
        _PROCESSORS = list(processors)
    if wrapper_class is not None:
        _WRAPPER_CLASS = wrapper_class
    if logger_factory is not None:
        _LOGGER_FACTORY = logger_factory  # pragma: no cover - configuration hook
    # cache_logger_on_first_use is ignored in this lightweight implementation


def get_logger(name: str | None = None) -> stdlib.BoundLogger:
    logger = _LOGGER_FACTORY(name)
    return _WRAPPER_CLASS(logger)


__all__ = [
    "configure",
    "get_logger",
    "processors",
    "stdlib",
    "dev",
]
