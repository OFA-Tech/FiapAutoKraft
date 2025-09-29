from __future__ import annotations

import threading
from collections import defaultdict
from typing import Callable, DefaultDict, Generic, Hashable, Iterable, TypeVar

Event = TypeVar("Event")
Subscriber = Callable[[Event], None]


class EventBus(Generic[Event]):
    """Thread-safe publish/subscribe bus."""

    def __init__(self) -> None:
        self._subscribers: DefaultDict[Hashable, list[Subscriber]] = defaultdict(list)
        self._lock = threading.RLock()

    def subscribe(self, key: Hashable, callback: Subscriber) -> None:
        with self._lock:
            self._subscribers[key].append(callback)

    def unsubscribe(self, key: Hashable, callback: Subscriber) -> None:
        with self._lock:
            listeners = self._subscribers.get(key)
            if not listeners:
                return
            try:
                listeners.remove(callback)
            except ValueError:
                return
            if not listeners:
                self._subscribers.pop(key, None)

    def publish(self, key: Hashable, event: Event) -> None:
        with self._lock:
            listeners: Iterable[Subscriber] = tuple(self._subscribers.get(key, ()))
        for listener in listeners:
            listener(event)
