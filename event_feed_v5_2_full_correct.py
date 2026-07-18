from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QObject, QTimer, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox, QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QPushButton, QVBoxLayout, QWidget
)

from ..events import EventLevel, PlatformEvent


LEVEL_COLORS = {
    EventLevel.DEBUG: "#9b8aa8",
    EventLevel.INFO: "#31b7ff",
    EventLevel.SUCCESS: "#35df83",
    EventLevel.WARNING: "#ffd166",
    EventLevel.ERROR: "#ff5c7a",
    EventLevel.AI: "#c000ff",
}

LEVEL_ICONS = {
    EventLevel.DEBUG: "·",
    EventLevel.INFO: "i",
    EventLevel.SUCCESS: "✓",
    EventLevel.WARNING: "!",
    EventLevel.ERROR: "×",
    EventLevel.AI: "✦",
}


class EventBridge(QObject):
    received = Signal(object)


class EventCard(QFrame):
    def __init__(self, event: PlatformEvent):
        super().__init__()
        self.platform_event = event
        self.setObjectName("panel")
        color = LEVEL_COLORS[event.level]
        self.setStyleSheet(
            f"QFrame#panel {{ border-left: 4px solid {color}; }}"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 9, 12, 9)
        top = QHBoxLayout()
        icon = QLabel(LEVEL_ICONS[event.level])
        icon.setStyleSheet(
            f"color:{color};font-size:18px;font-weight:900;"
        )
        title = QLabel(event.title or event.category.upper())
        title.setStyleSheet("font-weight:800;")
        timestamp = QLabel(self.display_time(event.timestamp))
        timestamp.setObjectName("muted")
        top.addWidget(icon)
        top.addWidget(title)
        top.addStretch()
        top.addWidget(timestamp)
        layout.addLayout(top)

        message = QLabel(event.message)
        message.setWordWrap(True)
        layout.addWidget(message)

        details = []
        if event.module:
            details.append(f"module: {event.module}")
        if event.scan_id is not None:
            details.append(f"scan: #{event.scan_id}")
        if event.metadata:
            details.extend(
                f"{key}: {value}" for key, value in event.metadata.items()
                if value not in (None, "", [], {})
            )
        if details:
            metadata = QLabel("  •  ".join(details))
            metadata.setObjectName("muted")
            metadata.setWordWrap(True)
            layout.addWidget(metadata)

    @staticmethod
    def display_time(value: str) -> str:
        try:
            return datetime.fromisoformat(value).astimezone().strftime("%H:%M:%S")
        except ValueError:
            return value


class Toast(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("panel")
        self.setVisible(False)
        self.setFixedWidth(330)
        layout = QVBoxLayout(self)
        self.title = QLabel()
        self.title.setStyleSheet("font-weight:900;")
        self.message = QLabel()
        self.message.setWordWrap(True)
        layout.addWidget(self.title)
        layout.addWidget(self.message)
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.hide)

    def show_event(self, event: PlatformEvent):
        if event.level not in {
            EventLevel.SUCCESS, EventLevel.WARNING, EventLevel.ERROR
        }:
            return
        self.title.setText(event.title or event.level.value.upper())
        self.message.setText(event.message)
        self.adjustSize()
        if self.parent():
            rect = self.parent().rect()
            self.move(rect.right() - self.width() - 24, 24)
        self.show()
        self.raise_()
        self.timer.start(3200)


class EventFeedPage(QWidget):
    event_selected = Signal(object)

    def __init__(self, event_bus, event_store):
        super().__init__()
        self.event_bus = event_bus
        self.event_store = event_store
        self.bridge = EventBridge()
        self.bridge.received.connect(self.on_event)
        self.event_bus.subscribe(self.bridge.received.emit)

        root = QVBoxLayout(self)
        title = QLabel("Live Event Feed")
        title.setObjectName("pageTitle")
        subtitle = QLabel(
            "A persistent, real-time stream from scans, AI, reports, cases, plugins, and the platform."
        )
        subtitle.setObjectName("muted")
        root.addWidget(title)
        root.addWidget(subtitle)

        filters = QHBoxLayout()
        self.category = QComboBox()
        self.category.addItem("All categories", "all")
        for category in self.event_store.categories():
            self.category.addItem(category.title(), category)

        self.level = QComboBox()
        self.level.addItem("All levels", "all")
        for value in EventLevel:
            self.level.addItem(value.value.title(), value.value)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search event titles or messages...")
        refresh = QPushButton("REFRESH")
        clear = QPushButton("CLEAR FEED")
        refresh.clicked.connect(self.refresh)
        clear.clicked.connect(self.clear_feed)
        self.category.currentIndexChanged.connect(self.refresh)
        self.level.currentIndexChanged.connect(self.refresh)
        self.search.returnPressed.connect(self.refresh)

        filters.addWidget(self.category)
        filters.addWidget(self.level)
        filters.addWidget(self.search, 1)
        filters.addWidget(refresh)
        filters.addWidget(clear)
        root.addLayout(filters)

        self.list = QListWidget()
        self.list.setSpacing(7)
        self.list.itemClicked.connect(self.select_item)
        root.addWidget(self.list, 1)
        self.refresh()

    def closeEvent(self, event):
        self.event_bus.unsubscribe(self.bridge.received.emit)
        super().closeEvent(event)

    def select_item(self, item):
        event = item.data(Qt.ItemDataRole.UserRole)
        if event:
            self.event_selected.emit(event)

    def add_card(self, event: PlatformEvent):
        item = QListWidgetItem()
        item.setData(Qt.ItemDataRole.UserRole, event)
        card = EventCard(event)
        item.setSizeHint(card.sizeHint())
        self.list.addItem(item)
        self.list.setItemWidget(item, card)
        self.list.scrollToBottom()

    def on_event(self, event: PlatformEvent):
        category = self.category.currentData()
        level = self.level.currentData()
        search = self.search.text().strip().lower()
        visible = (
            (category == "all" or event.category == category)
            and (level == "all" or event.level.value == level)
            and (
                not search
                or search in event.title.lower()
                or search in event.message.lower()
            )
        )
        if visible:
            self.add_card(event)

    def refresh(self):
        self.list.clear()
        for event in self.event_store.recent(
            300,
            category=self.category.currentData(),
            level=self.level.currentData(),
            search=self.search.text().strip() or None,
        ):
            self.add_card(event)

        known = {
            self.category.itemData(index)
            for index in range(self.category.count())
        }
        for category in self.event_store.categories():
            if category not in known:
                self.category.addItem(category.title(), category)

    def clear_feed(self):
        self.event_store.clear()
        self.refresh()
