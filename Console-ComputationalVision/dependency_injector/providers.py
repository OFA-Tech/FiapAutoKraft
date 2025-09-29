"""Minimal provider implementations used by the project tests."""

from __future__ import annotations

from typing import Any, Callable, Dict


class ProviderTemplate:
    """Base template for providers defined on declarative containers."""

    def __init__(self, factory: Callable[..., Any], *args: Any, scope: str | None = None, **kwargs: Any) -> None:
        self.factory = factory
        self.args = args
        self.kwargs = kwargs
        self.scope = scope
        self._name: str | None = None

    def __set_name__(self, owner: type, name: str) -> None:  # pragma: no cover - descriptor hook
        self._name = name

    @property
    def name(self) -> str:
        if self._name is None:  # pragma: no cover - defensive
            raise RuntimeError("Provider template is not bound to a container attribute.")
        return self._name

    def bind(self, container: "DeclarativeContainer", name: str) -> "BoundProvider":
        raise NotImplementedError

    def clone(self) -> "ProviderTemplate":
        return self.__class__(self.factory, *self.args, scope=self.scope, **self.kwargs)


class BoundProvider:
    """Runtime provider bound to a specific container instance."""

    def __init__(self, template: ProviderTemplate, container: "DeclarativeContainer", name: str) -> None:
        self.template = template
        self.container = container
        self.name = name
        self._overrides: list[BoundProvider] = []

    def override(self, other: "BoundProvider") -> None:
        if other.container is not self.container:
            raise ValueError("Can only override providers from the same container instance.")
        self.container._clear_cache(self.name)
        self._overrides.append(other)

    def _resolve_argument(self, value: Any) -> Any:
        if isinstance(value, BoundProvider):
            return value()
        if isinstance(value, ProviderTemplate):
            bound = self.container._bound_providers[value.name]
            return bound()
        return value

    def _resolve_args(self) -> tuple[tuple[Any, ...], Dict[str, Any]]:
        args = tuple(self._resolve_argument(arg) for arg in self.template.args)
        kwargs = {key: self._resolve_argument(value) for key, value in self.template.kwargs.items()}
        return args, kwargs

    def reset_scope(self, scope_name: str) -> None:
        # Base implementation does nothing; subclasses override when needed.
        return None

    def __call__(self) -> Any:
        raise NotImplementedError


class BoundSingletonProvider(BoundProvider):
    def __call__(self) -> Any:
        if self._overrides:
            return self._overrides[-1]()
        scope = self.template.scope or "singleton"
        cache = self.container._scope_caches.setdefault(scope, {})
        if self.name in cache:
            return cache[self.name]
        args, kwargs = self._resolve_args()
        instance = self.template.factory(*args, **kwargs)
        cache[self.name] = instance
        return instance

    def reset_scope(self, scope_name: str) -> None:
        if (self.template.scope or "singleton") == scope_name:
            cache = self.container._scope_caches.get(scope_name)
            if cache and self.name in cache:
                del cache[self.name]


class BoundFactoryProvider(BoundProvider):
    def __call__(self) -> Any:
        if self._overrides:
            return self._overrides[-1]()
        args, kwargs = self._resolve_args()
        return self.template.factory(*args, **kwargs)


class Singleton(ProviderTemplate):
    def bind(self, container: "DeclarativeContainer", name: str) -> BoundSingletonProvider:
        return BoundSingletonProvider(self, container, name)


class Factory(ProviderTemplate):
    def bind(self, container: "DeclarativeContainer", name: str) -> BoundFactoryProvider:
        return BoundFactoryProvider(self, container, name)


__all__ = [
    "ProviderTemplate",
    "BoundProvider",
    "Singleton",
    "Factory",
]
