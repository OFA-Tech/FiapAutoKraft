"""Simplified implementation of :mod:`pydantic_settings` for local testing."""

from __future__ import annotations

import os
from typing import Any, Dict


class SettingsConfigDict(dict):
    """Container for BaseSettings configuration options."""


class BaseSettings:
    """Very small subset of Pydantic's BaseSettings."""

    model_config: SettingsConfigDict = SettingsConfigDict()

    def __init__(self, **overrides: Any) -> None:
        config = dict(self.model_config)
        prefix = config.get("env_prefix", "")
        env_file = config.get("env_file")
        if env_file and os.path.exists(env_file):
            self._load_env_file(env_file)
        for name in self.__class__.__annotations__:
            value = self._resolve_value(name, prefix, overrides)
            setattr(self, name, value)

    def _resolve_value(self, name: str, prefix: str, overrides: Dict[str, Any]) -> Any:
        if name in overrides:
            return overrides[name]
        env_name = prefix + name.upper()
        if env_name in os.environ:
            return self._coerce(name, os.environ[env_name])
        return self._coerce(name, getattr(self.__class__, name))

    def _coerce(self, name: str, value: Any) -> Any:
        annotation = self.__class__.__annotations__.get(name)
        if annotation in (int, float, bool):
            try:
                return annotation(value)
            except Exception:  # pragma: no cover - defensive
                return value
        return value

    @staticmethod
    def _load_env_file(path: str) -> None:
        with open(path, "r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip())


__all__ = ["BaseSettings", "SettingsConfigDict"]
