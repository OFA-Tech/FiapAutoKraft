from __future__ import annotations

from shared.bus import EventBus


def test_event_bus_publish_and_unsubscribe() -> None:
    bus: EventBus[str] = EventBus()
    received: list[str] = []

    def listener(event: str) -> None:
        received.append(event)

    bus.subscribe("topic", listener)
    bus.publish("topic", "hello")
    assert received == ["hello"]

    bus.unsubscribe("topic", listener)
    bus.publish("topic", "ignored")
    assert received == ["hello"]
