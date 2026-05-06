"""EventBus — synchronous pub/sub within a session."""

from __future__ import annotations

from collections import defaultdict
from typing import Callable, Type, TypeVar

from core.events.types import BaseEvent

E = TypeVar("E", bound=BaseEvent)
Handler = Callable[[BaseEvent], None]


class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[type, list[Handler]] = defaultdict(list)
        self._global: list[Handler] = []

    def subscribe(self, event_type: Type[E], handler: Callable[[E], None]) -> None:
        self._handlers[event_type].append(handler)  # type: ignore[arg-type]

    def subscribe_all(self, handler: Handler) -> None:
        """Receive every event regardless of type."""
        self._global.append(handler)

    def publish(self, event: BaseEvent) -> None:
        for h in self._global:
            h(event)
        for h in self._handlers.get(type(event), []):
            h(event)

    def clear(self) -> None:
        self._handlers.clear()
        self._global.clear()
