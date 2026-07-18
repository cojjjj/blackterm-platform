from __future__ import annotations

from collections import deque
from datetime import datetime

from PySide6.QtCore import (
    QEasingCurve,
    QObject,
    QPoint,
    QPropertyAnimation,
    QSequentialAnimationGroup,
    QTimer,
    Qt,
    Signal,
)
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
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
    EventLevel.DEBUG: "\u00b7",
    EventLevel.INFO: "i",
    EventLevel.SUCCESS: "\u2713",
    EventLevel.WARNING: "!",
    EventLevel.ERROR: "\u00d7",
    EventLevel.AI: "\u2726",
}
DETAIL_SEPARATOR = "  \u2022  "


class EventBridge(QObject):
    received = Signal(object)


class EventCard(QFrame):
    def __init__(self, event: PlatformEvent):
        super().__init__()
        self.platform_event = event
        self.setObjectName("panel")
        color = LEVEL_COLORS.get(event.level, "#9b8aa8")
        self.setStyleSheet(f"QFrame#panel {{ border-left: 4px solid {color}; }}")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 9, 12, 9)
        top = QHBoxLayout()
        icon = QLabel(LEVEL_ICONS.get(event.level, "\u00b7"))
        icon.setStyleSheet(f"color:{color};font-size:18px;font-weight:900;")
        title = QLabel(event.title or event.category.upper())
        title.setStyleSheet("font-weight:800;")
        timestamp = QLabel(self.display_time(event.timestamp))
        timestamp.setObjectName("muted")
        top.addWidget(icon)
        top.addWidget(title)
        top.addStretch()
        top.addWidget(timestamp)
        layout.addLayout(top)

        message = QLabel(event.message or "No additional event details.")
        message.setWordWrap(True)
        message.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(message)

        details = []
        if event.module:
            details.append(f"module: {event.module}")
        if event.scan_id is not None:
            details.append(f"scan: #{event.scan_id}")
        if event.metadata:
            details.extend(
                f"{key}: {value}"
                for key, value in event.metadata.items()
                if value not in (None, "", [], {})
            )
        if details:
            metadata = QLabel(DETAIL_SEPARATOR.join(details))
            metadata.setObjectName("muted")
            metadata.setWordWrap(True)
            metadata.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            layout.addWidget(metadata)

    @staticmethod
    def display_time(value: str) -> str:
        try:
            return datetime.fromisoformat(value).astimezone().strftime("%H:%M:%S")
        except (TypeError, ValueError):
            return str(value)


class Toast(QFrame):
    """Queued bottom-right toast with slide/fade motion."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("panel")
        self.setVisible(False)
        self.setFixedWidth(350)
        self._queue = deque()
        self._active = False
        layout = QVBoxLayout(self)
        self.title = QLabel()
        self.title.setStyleSheet("font-weight:900;")
        self.message = QLabel()
        self.message.setWordWrap(True)
        layout.addWidget(self.title)
        layout.addWidget(self.message)
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self._hide_animated)

    def show_event(self, event: PlatformEvent):
        if event.level not in {
            EventLevel.SUCCESS,
            EventLevel.WARNING,
            EventLevel.ERROR,
            EventLevel.AI,
        }:
            return
        self._queue.append(event)
        if not self._active:
            self._show_next()

    def _show_next(self):
        if not self._queue:
            self._active = False
            return
        self._active = True
        event = self._queue.popleft()
        color = LEVEL_COLORS.get(event.level, "#31b7ff")
        icon = LEVEL_ICONS.get(event.level, "i")
        self.title.setText(f"{icon}  {event.title or event.level.value.upper()}")
        self.title.setStyleSheet(f"font-weight:900;color:{color};")
        self.message.setText(event.message)
        self.adjustSize()
        parent = self.parentWidget()
        if not parent:
            return
        rect = parent.rect()
        end = QPoint(rect.right() - self.width() - 24, rect.bottom() - self.height() - 24)
        start = QPoint(rect.right() + 20, end.y())
        self.move(start)
        self.setWindowOpacity(0.0)
        self.show()
        self.raise_()

        move = QPropertyAnimation(self, b"pos", self)
        move.setDuration(260)
        move.setStartValue(start)
        move.setEndValue(end)
        move.setEasingCurve(QEasingCurve.OutCubic)
        fade = QPropertyAnimation(self, b"windowOpacity", self)
        fade.setDuration(220)
        fade.setStartValue(0.0)
        fade.setEndValue(1.0)
        move.start()
        fade.start()
        self._show_move = move
        self._show_fade = fade
        self.timer.start(3600)

    def _hide_animated(self):
        fade = QPropertyAnimation(self, b"windowOpacity", self)
        fade.setDuration(180)
        fade.setStartValue(1.0)
        fade.setEndValue(0.0)
        fade.finished.connect(self._finish_hide)
        fade.start()
        self._hide_fade = fade

    def _finish_hide(self):
        self.hide()
        self.setWindowOpacity(1.0)
        self._show_next()


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

        counter_row = QHBoxLayout()
        counter_row.addWidget(QLabel("VISIBLE EVENTS"))
        self.counter = QLabel("0")
        self.counter.setObjectName("metricValue")
        counter_row.addWidget(self.counter)
        counter_row.addStretch()
        root.addLayout(counter_row)

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
        self.counter.setText(str(self.list.count()))
        animation = QPropertyAnimation(card, b"windowOpacity", self)
        animation.setDuration(220)
        animation.setStartValue(0.0)
        animation.setEndValue(1.0)
        animation.start()
        self._last_card_animation = animation

    def on_event(self, event: PlatformEvent):
        category = self.category.currentData()
        level = self.level.currentData()
        search = self.search.text().strip().lower()
        title = (event.title or "").lower()
        message = (event.message or "").lower()
        visible = (
            (category == "all" or event.category == category)
            and (level == "all" or event.level.value == level)
            and (not search or search in title or search in message)
        )
        if visible:
            self.add_card(event)

    def refresh(self):
        self.list.clear()
        self.counter.setText("0")
        for event in self.event_store.recent(
            300,
            category=self.category.currentData(),
            level=self.level.currentData(),
            search=self.search.text().strip() or None,
        ):
            self.add_card(event)

        known = {self.category.itemData(index) for index in range(self.category.count())}
        for category in self.event_store.categories():
            if category not in known:
                self.category.addItem(category.title(), category)

    def clear_feed(self):
        self.event_store.clear()
        self.list.clear()
        self.counter.setText("0")
