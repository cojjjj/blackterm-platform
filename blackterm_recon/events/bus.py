from __future__ import annotations

from collections import defaultdict, deque
from collections.abc import Callable
import logging
from threading import RLock
from uuid import uuid4

from .models import EventLevel, PlatformEvent
from .store import EventStore

Subscriber = Callable[[PlatformEvent], None]
LOGGER = logging.getLogger("blackterm_recon.events")


class EventBus:
    """Thread-safe event bus with durable history and isolated subscribers."""

    def __init__(self, store: EventStore | None = None, history_size: int = 250):
        self.store = store
        self._subscribers: dict[str, dict[str, Subscriber]] = defaultdict(dict)
        self._lock = RLock()
        self._history: deque[PlatformEvent] = deque(maxlen=max(10, history_size))

    def subscribe(self, callback: Subscriber, category: str = "*") -> str:
        token = uuid4().hex
        with self._lock:
            self._subscribers[category][token] = callback
        return token

    def unsubscribe(self, callback_or_token, category: str = "*") -> None:
        with self._lock:
            bucket = self._subscribers.get(category, {})
            if isinstance(callback_or_token, str):
                bucket.pop(callback_or_token, None)
            else:
                stale = [token for token, callback in bucket.items() if callback == callback_or_token]
                for token in stale:
                    bucket.pop(token, None)

    def recent(self, limit: int = 50) -> list[PlatformEvent]:
        with self._lock:
            return list(self._history)[-max(0, limit):]

    def publish(self, event: PlatformEvent) -> PlatformEvent:
        if self.store:
            try:
                self.store.save(event)
            except Exception:
                LOGGER.exception("Failed to persist platform event")

        with self._lock:
            self._history.append(event)
            callbacks = list(self._subscribers.get("*", {}).values())
            callbacks.extend(self._subscribers.get(event.category, {}).values())

        for callback in callbacks:
            try:
                callback(event)
            except Exception:
                LOGGER.exception("Platform event subscriber failed")
        return event

    def emit(self, category: str, message: str, *, title: str = "",
             level: EventLevel = EventLevel.INFO, scan_id: int | None = None,
             module: str = "platform", metadata: dict | None = None) -> PlatformEvent:
        return self.publish(PlatformEvent(
            category=category,
            message=message,
            title=title,
            level=level,
            scan_id=scan_id,
            module=module,
            metadata=metadata or {},
        ))
