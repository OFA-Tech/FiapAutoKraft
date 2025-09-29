"""Logging configuration helpers using structlog."""

from __future__ import annotations

import logging
from typing import Any

import structlog


def setup_logging(level: str = "INFO") -> None:
    """Initialise structlog and the standard logging bridge."""

    logging.basicConfig(
        level=level,
        format="%(message)s",
    )
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str, **kwargs: Any) -> structlog.stdlib.BoundLogger:
    """Return a configured structlog logger bound to ``name``."""

    logger = structlog.get_logger(name)
    if kwargs:
        logger = logger.bind(**kwargs)
    return logger


__all__ = ["setup_logging", "get_logger"]
