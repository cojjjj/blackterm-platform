from __future__ import annotations

from PySide6.QtCore import QObject, Qt, Signal, Slot


class QtEventBridge(QObject):
    """Moves platform events onto the Qt GUI thread safely."""

    event_received = Signal(object)

    def __init__(self, event_bus, parent: QObject | None = None):
        super().__init__(parent)
        self.event_bus = event_bus
        if self.event_bus:
            self.event_bus.subscribe(self._relay)

    def _relay(self, event) -> None:
        self.event_received.emit(event)

    def connect(self, callback) -> None:
        self.event_received.connect(callback, Qt.QueuedConnection)

    @Slot()
    def close(self) -> None:
        if self.event_bus:
            self.event_bus.unsubscribe(self._relay)
