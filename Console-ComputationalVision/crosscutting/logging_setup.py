"""Logging utilities using Python's standard logging module."""

from __future__ import annotations

import logging
from logging import Logger


def setup_logging(level: str = "INFO") -> None:
    """Configure the root logger with a sensible default format."""

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        datefmt="%H:%M:%S",
    )


def get_logger(name: str) -> Logger:
    """Return a module-level logger."""

    return logging.getLogger(name)


__all__ = ["setup_logging", "get_logger"]
