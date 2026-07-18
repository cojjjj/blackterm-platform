from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from threading import RLock

from .models import EventLevel, PlatformEvent
from .store import EventStore


Subscriber = Callable[[PlatformEvent], None]


class EventBus:
    def __init__(self, store: EventStore | None = None):
        self.store = store
        self._subscribers: dict[str, list[Subscriber]] = defaultdict(list)
        self._lock = RLock()

    def subscribe(self, callback: Subscriber, category: str = "*") -> None:
        with self._lock:
            if callback not in self._subscribers[category]:
                self._subscribers[category].append(callback)

    def unsubscribe(self, callback: Subscriber, category: str = "*") -> None:
        with self._lock:
            if callback in self._subscribers.get(category, []):
                self._subscribers[category].remove(callback)

    def publish(self, event: PlatformEvent) -> PlatformEvent:
        if self.store:
            self.store.save(event)

        with self._lock:
            callbacks = list(self._subscribers.get("*", []))
            callbacks.extend(self._subscribers.get(event.category, []))

        for callback in callbacks:
            try:
                callback(event)
            except Exception:
                # A feed subscriber must never break the engine.
                continue
        return event

    def emit(
        self,
        category: str,
        message: str,
        *,
        title: str = "",
        level: EventLevel = EventLevel.INFO,
        scan_id: int | None = None,
        module: str = "platform",
        metadata: dict | None = None,
    ) -> PlatformEvent:
        return self.publish(
            PlatformEvent(
                category=category,
                message=message,
                title=title,
                level=level,
                scan_id=scan_id,
                module=module,
                metadata=metadata or {},
            )
        )
