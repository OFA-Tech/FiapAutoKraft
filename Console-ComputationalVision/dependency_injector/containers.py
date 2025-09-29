"""Simplified declarative container implementation."""

from __future__ import annotations

from contextlib import AbstractContextManager
from typing import Dict, Iterator

from .providers import ProviderTemplate


class DeclarativeContainer:
    """Container that binds provider templates declared on subclasses."""

    def __init__(self) -> None:
        self._bound_providers: Dict[str, object] = {}
        self._scope_caches: Dict[str, Dict[str, object]] = {"singleton": {}}
        self._scope_stack: list[str] = ["singleton"]
        for name, attribute in self.__class__.__dict__.items():
            if isinstance(attribute, ProviderTemplate):
                bound = attribute.bind(self, name)
                self._bound_providers[name] = bound
                setattr(self, name, bound)

    def _clear_cache(self, name: str) -> None:
        for cache in self._scope_caches.values():
            cache.pop(name, None)

    def enter_scope(self, scope_name: str) -> AbstractContextManager["DeclarativeContainer"]:
        return _ScopeContext(self, scope_name)


class _ScopeContext(AbstractContextManager[DeclarativeContainer]):
    def __init__(self, container: DeclarativeContainer, scope_name: str) -> None:
        self._container = container
        self._scope_name = scope_name

    def __enter__(self) -> DeclarativeContainer:
        self._container._scope_stack.append(self._scope_name)
        self._container._scope_caches.setdefault(self._scope_name, {})
        return self._container

    def __exit__(self, exc_type, exc, exc_tb) -> bool:
        for provider in self._container._bound_providers.values():
            provider.reset_scope(self._scope_name)
        self._container._scope_caches.pop(self._scope_name, None)
        self._container._scope_stack.pop()
        return False


__all__ = ["DeclarativeContainer"]
