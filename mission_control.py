from __future__ import annotations

from collections import deque

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QProgressBar, QVBoxLayout, QWidget
)

from ...events import EventLevel
from ..widgets import MetricCard, PulseDot, Sparkline


class MissionBridge(QObject):
    event_received = Signal(object)


class MissionControlPage(QWidget):
    def __init__(self, engine, event_bus, event_store):
        super().__init__()
        self.engine = engine
        self.event_bus = event_bus
        self.event_store = event_store
        self.running_scans = 0
        self.recent_levels = deque(maxlen=50)

        root = QVBoxLayout(self)

        top = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("BLACKTERM Mission Control")
        title.setObjectName("pageTitle")
        subtitle = QLabel(
            "Live platform health, scan activity, event intelligence, and operator awareness."
        )
        subtitle.setObjectName("muted")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        top.addLayout(title_box)
        top.addStretch()
        top.addWidget(PulseDot())
        self.state = QLabel("PLATFORM ONLINE")
        self.state.setObjectName("statusActive")
        top.addWidget(self.state)
        root.addLayout(top)

        metrics = QHBoxLayout()
        self.hosts = MetricCard("Observed Hosts", "0", "Unique saved targets")
        self.open_ports = MetricCard("Open Ports", "0", "Across saved scans")
        self.running = MetricCard("Running Scans", "0", "Live engine activity")
        self.alerts = MetricCard("Alerts", "0", "Warnings and errors")
        self.events = MetricCard("Events", "0", "Persistent event history")
        for card in (
            self.hosts,
            self.open_ports,
            self.running,
            self.alerts,
            self.events,
        ):
            metrics.addWidget(card)
        root.addLayout(metrics)

        body = QGridLayout()

        feed_panel = QFrame()
        feed_panel.setObjectName("panel")
        feed_layout = QVBoxLayout(feed_panel)
        feed_layout.addWidget(QLabel("LIVE INTELLIGENCE FEED"))
        self.feed = QListWidget()
        self.feed.setSpacing(4)
        feed_layout.addWidget(self.feed)

        map_panel = QFrame()
        map_panel.setObjectName("panel")
        map_layout = QVBoxLayout(map_panel)
        map_layout.addWidget(QLabel("EVENT ACTIVITY"))
        self.sparkline = Sparkline()
        map_layout.addWidget(self.sparkline)
        map_layout.addWidget(QLabel("PLATFORM LOAD"))
        self.load = QProgressBar()
        self.load.setRange(0, 100)
        map_layout.addWidget(self.load)

        status_panel = QFrame()
        status_panel.setObjectName("panel")
        status_layout = QVBoxLayout(status_panel)
        status_layout.addWidget(QLabel("THREAT / EXPOSURE CONTEXT"))
        self.threat = QLabel()
        self.threat.setWordWrap(True)
        self.threat.setObjectName("muted")
        status_layout.addWidget(self.threat)
        status_layout.addStretch()

        body.addWidget(feed_panel, 0, 0, 2, 2)
        body.addWidget(map_panel, 0, 2)
        body.addWidget(status_panel, 1, 2)
        root.addLayout(body, 1)

        self.bridge = MissionBridge()
        self.bridge.event_received.connect(self.on_event)
        if self.event_bus:
            self.event_bus.subscribe(self.bridge.event_received.emit)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(1000)
        self.refresh()

    def refresh(self):
        scan_stats = self.engine.repository.stats()
        event_stats = self.event_store.stats()

        rows = self.engine.repository.list_recent(500)
        unique_hosts = len({row["ip"] for row in rows})

        self.hosts.set_value(unique_hosts)
        self.open_ports.set_value(scan_stats["open_ports"])
        self.running.set_value(self.running_scans)
        self.alerts.set_value(event_stats["warnings"] + event_stats["errors"])
        self.events.set_value(event_stats["total"])

        self.sparkline.set_values(self.event_store.recent_counts())
        load_value = min(
            100,
            int(
                (event_stats["warnings"] * 3)
                + (event_stats["errors"] * 7)
                + self.running_scans * 15
            ),
        )
        self.load.setValue(load_value)

        if event_stats["errors"]:
            level = "ELEVATED"
            context = (
                f"{event_stats['errors']} error event(s) and "
                f"{event_stats['warnings']} warning event(s) are recorded."
            )
        elif event_stats["warnings"]:
            level = "GUARDED"
            context = (
                f"{event_stats['warnings']} warning event(s) are recorded. "
                "Review unexpected service exposure and failed operations."
            )
        else:
            level = "LOW"
            context = (
                "No error or warning events are currently recorded. "
                "This does not imply the environment is vulnerability-free."
            )
        self.threat.setText(
            f"PLATFORM CONTEXT: {level}\n\n"
            f"{context}\n\n"
            f"Completed scans: {event_stats['completed_scans']}\n"
            f"AI events: {event_stats['ai']}\n"
            f"Last scan: {scan_stats['last_scan']}"
        )

    def on_event(self, event):
        if event.title == "Scan Started":
            self.running_scans += 1
        elif event.title == "Scan Complete":
            self.running_scans = max(0, self.running_scans - 1)

        color = {
            EventLevel.INFO: "#31b7ff",
            EventLevel.SUCCESS: "#35df83",
            EventLevel.WARNING: "#ffd166",
            EventLevel.ERROR: "#ff5c7a",
            EventLevel.AI: "#c000ff",
            EventLevel.DEBUG: "#9b8aa8",
        }[event.level]
        symbol = {
            EventLevel.INFO: "i",
            EventLevel.SUCCESS: "✓",
            EventLevel.WARNING: "!",
            EventLevel.ERROR: "×",
            EventLevel.AI: "✦",
            EventLevel.DEBUG: "·",
        }[event.level]

        item = QListWidgetItem(
            f"{symbol}  {event.title or event.category.upper()}  —  {event.message}"
        )
        item.setForeground(QBrush(QColor(color)))
        self.feed.addItem(item)
        while self.feed.count() > 80:
            self.feed.takeItem(0)
        self.feed.scrollToBottom()
        self.refresh()
