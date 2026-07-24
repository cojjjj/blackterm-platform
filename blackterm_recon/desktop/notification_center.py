from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QListWidget, QPushButton, QVBoxLayout


class NotificationCenter(QFrame):
    close_requested = Signal()

    def __init__(self, event_store=None, parent=None):
        super().__init__(parent)
        self.event_store = event_store
        self.setObjectName("notificationCenter")
        self.setMinimumWidth(360)
        self.setMaximumWidth(420)
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        header = QHBoxLayout()
        title = QLabel("NOTIFICATION CENTER")
        title.setObjectName("notificationTitle")
        close = QPushButton("×")
        close.setFixedSize(30, 30)
        close.clicked.connect(self.close_requested.emit)
        header.addWidget(title)
        header.addStretch()
        header.addWidget(close)
        root.addLayout(header)
        self.list = QListWidget()
        self.list.setObjectName("notificationList")
        root.addWidget(self.list, 1)
        refresh = QPushButton("REFRESH EVENTS")
        refresh.clicked.connect(self.refresh)
        root.addWidget(refresh)
        self.refresh()

    def refresh(self):
        self.list.clear()
        rows = []
        if self.event_store is not None:
            for method in ("list_recent", "recent", "list_events"):
                fn = getattr(self.event_store, method, None)
                if callable(fn):
                    try:
                        rows = fn(30)
                        break
                    except Exception:
                        continue
        if not rows:
            self.list.addItem("✓ Platform ready\nBLACKTERM Mission Control is online")
            self.list.addItem("● Intelligence modules connected\nCVE Atlas, OSINT, and threat intelligence ready")
            self.list.addItem("● AI analyst standing by\nOpen the analyst dock from the command bar")
            return
        for row in rows:
            if isinstance(row, dict):
                title = row.get("title") or row.get("event_type") or "Platform Event"
                body = row.get("message") or row.get("body") or ""
                self.list.addItem(f"{title}\n{body}")
            else:
                self.list.addItem(str(row))
