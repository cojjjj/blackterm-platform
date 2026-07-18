from __future__ import annotations

from collections import deque
from datetime import datetime

from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtGui import QBrush, QColor, QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from ...events import EventLevel
from ..widgets import MetricCard, PulseDot, Sparkline, ThreatMeter, TypingLabel


LEVEL_COLORS = {
    EventLevel.INFO: "#31b7ff",
    EventLevel.SUCCESS: "#35df83",
    EventLevel.WARNING: "#ffd166",
    EventLevel.ERROR: "#ff5c7a",
    EventLevel.AI: "#c000ff",
    EventLevel.DEBUG: "#9b8aa8",
}
LEVEL_SYMBOLS = {
    EventLevel.INFO: "i",
    EventLevel.SUCCESS: "\u2713",
    EventLevel.WARNING: "!",
    EventLevel.ERROR: "\u00d7",
    EventLevel.AI: "\u2726",
    EventLevel.DEBUG: "\u00b7",
}
EVENT_SEPARATOR = " \u2014 "


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
        self.scan_phase = 0

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

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
        metrics.setSpacing(8)
        self.hosts = MetricCard("Observed Hosts", "0", "Unique saved targets")
        self.open_ports = MetricCard("Open Ports", "0", "Across saved scans")
        self.running = MetricCard("Running Scans", "0", "Live engine activity")
        self.alerts = MetricCard("Alerts", "0", "Warnings and errors")
        self.events = MetricCard("Events", "0", "Persistent event history")
        for card in (self.hosts, self.open_ports, self.running, self.alerts, self.events):
            metrics.addWidget(card)
        root.addLayout(metrics)

        body = QGridLayout()
        body.setHorizontalSpacing(8)
        body.setVerticalSpacing(8)
        body.setColumnStretch(0, 2)
        body.setColumnStretch(1, 3)
        body.setColumnStretch(2, 3)

        feed_panel = QFrame()
        feed_panel.setObjectName("panel")
        feed_layout = QVBoxLayout(feed_panel)
        feed_layout.setContentsMargins(10, 10, 10, 10)
        feed_layout.addWidget(QLabel("LIVE INTELLIGENCE FEED"))
        self.feed = QListWidget()
        self.feed.setObjectName("missionFeed")
        self.feed.setSpacing(5)
        self.feed.setWordWrap(True)
        self.feed.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.feed.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.feed.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.feed.setStyleSheet(
            "QListWidget#missionFeed { background: transparent; border: 1px solid #193957; padding: 6px; }"
            "QListWidget#missionFeed::item { border-bottom: 1px solid rgba(49, 183, 255, 35); padding: 8px 6px; }"
        )
        feed_layout.addWidget(self.feed)

        activity_panel = QFrame()
        activity_panel.setObjectName("panel")
        activity_layout = QVBoxLayout(activity_panel)
        activity_layout.addWidget(QLabel("EVENT ACTIVITY"))
        self.sparkline = Sparkline()
        activity_layout.addWidget(self.sparkline)
        activity_layout.addWidget(QLabel("PLATFORM LOAD"))
        self.load = QProgressBar()
        self.load.setRange(0, 100)
        activity_layout.addWidget(self.load)
        self.threat_meter = ThreatMeter()
        activity_layout.addWidget(self.threat_meter)

        ai_panel = QFrame()
        ai_panel.setObjectName("panel")
        ai_layout = QVBoxLayout(ai_panel)
        ai_layout.addWidget(QLabel("AI ANALYST"))
        self.ai_state = QLabel("STANDBY")
        self.ai_state.setObjectName("statusActive")
        self.ai_detail = TypingLabel(
            "Awaiting scan telemetry. BLACKTERM will summarize service exposure as events arrive.",
            interval=10,
        )
        self.ai_detail.setWordWrap(True)
        self.ai_detail.setObjectName("muted")
        self.ai_score = QProgressBar()
        self.ai_score.setRange(0, 100)
        self.ai_score.setValue(0)
        self.ai_score.setFormat("CONTEXT SCORE %p%")
        ai_layout.addWidget(self.ai_state)
        ai_layout.addWidget(self.ai_detail)
        ai_layout.addWidget(self.ai_score)
        ai_layout.addStretch()

        status_panel = QFrame()
        status_panel.setObjectName("panel")
        status_layout = QVBoxLayout(status_panel)
        status_layout.addWidget(QLabel("THREAT / EXPOSURE CONTEXT"))
        self.threat = QLabel()
        self.threat.setWordWrap(True)
        self.threat.setObjectName("muted")
        status_layout.addWidget(self.threat)
        status_layout.addStretch()

        timeline_panel = QFrame()
        timeline_panel.setObjectName("panel")
        timeline_layout = QVBoxLayout(timeline_panel)
        timeline_layout.addWidget(QLabel("CASE / ACTIVITY TIMELINE"))
        self.timeline = QListWidget()
        self.timeline.setObjectName("missionTimeline")
        self.timeline.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.timeline.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.timeline.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.timeline.setStyleSheet(
            "QListWidget#missionTimeline { background: transparent; border: none; }"
            "QListWidget#missionTimeline::item { padding: 5px 3px; border-left: 2px solid #4b245b; }"
        )
        timeline_layout.addWidget(self.timeline)

        body.addWidget(feed_panel, 0, 0, 3, 1)
        body.addWidget(activity_panel, 0, 1, 1, 2)
        body.addWidget(status_panel, 1, 1)
        body.addWidget(ai_panel, 1, 2)
        body.addWidget(timeline_panel, 2, 1, 1, 2)
        root.addLayout(body, 1)

        self.bridge = MissionBridge()
        self.bridge.event_received.connect(self.on_event)
        if self.event_bus:
            self.event_bus.subscribe(self.bridge.event_received.emit)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(1000)
        self.scan_timer = QTimer(self)
        self.scan_timer.setInterval(350)
        self.scan_timer.timeout.connect(self.animate_scan_state)
        self.refresh()

    def animate_scan_state(self):
        if not self.running_scans:
            self.scan_timer.stop()
            self.state.setText("PLATFORM ONLINE")
            return
        self.scan_phase = (self.scan_phase + 1) % 4
        self.state.setText("SCANNING" + "." * self.scan_phase)

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
            int(event_stats["warnings"] * 3 + event_stats["errors"] * 7 + self.running_scans * 15),
        )
        self.load.setValue(load_value)
        threat_score = min(
            100,
            event_stats["warnings"] * 12
            + event_stats["errors"] * 25
            + min(30, scan_stats["open_ports"] * 2),
        )
        self.threat_meter.set_value(threat_score)
        self.ai_score.setValue(min(100, threat_score + event_stats["ai"] * 4))

        if event_stats["errors"]:
            level = "ELEVATED"
            context = f"{event_stats['errors']} error event(s) and {event_stats['warnings']} warning event(s) are recorded."
        elif event_stats["warnings"]:
            level = "GUARDED"
            context = f"{event_stats['warnings']} warning event(s) are recorded. Review unexpected service exposure and failed operations."
        else:
            level = "LOW"
            context = "No error or warning events are currently recorded. This does not imply the environment is vulnerability-free."
        self.threat.setText(
            f"PLATFORM CONTEXT: {level}\n\n{context}\n\n"
            f"Completed scans: {event_stats['completed_scans']}\n"
            f"AI events: {event_stats['ai']}\n"
            f"Last scan: {scan_stats['last_scan']}"
        )

    def on_event(self, event):
        if event.title == "Scan Started":
            self.running_scans += 1
            self.ai_state.setText("ANALYZING TARGET")
            self.ai_detail.set_typed_text(event.message)
            self.scan_timer.start()
        elif event.title == "Open Port Observed":
            port = event.metadata.get("port", "?")
            service = event.metadata.get("service", "unknown")
            self.ai_state.setText("CORRELATING SERVICES")
            self.ai_detail.set_typed_text(f"Observed {service} on TCP/{port}. Evaluating exposure context and service risk.")
        elif event.level == EventLevel.AI:
            self.ai_state.setText("ANALYSIS READY")
            self.ai_detail.set_typed_text(event.message)
        elif event.title == "Scan Complete":
            self.running_scans = max(0, self.running_scans - 1)
            self.ai_state.setText("SCAN REVIEW COMPLETE")
            self.ai_detail.set_typed_text(event.message)
            if not self.running_scans:
                self.scan_timer.stop()
                self.state.setText("PLATFORM ONLINE")

        try:
            timeline_time = datetime.fromisoformat(event.timestamp).astimezone().strftime("%H:%M:%S")
        except (TypeError, ValueError):
            timeline_time = "--:--:--"
        timeline_item = QListWidgetItem(f"{timeline_time}   {event.title or event.category.upper()}")
        timeline_item.setToolTip(event.message or "")
        self.timeline.addItem(timeline_item)
        while self.timeline.count() > 10:
            self.timeline.takeItem(0)
        self.timeline.scrollToBottom()

        color = LEVEL_COLORS.get(event.level, "#9b8aa8")
        symbol = LEVEL_SYMBOLS.get(event.level, "\u00b7")
        title = event.title or event.category.upper()
        message = event.message or "No additional event details."
        try:
            timestamp = datetime.fromisoformat(event.timestamp).astimezone().strftime("%H:%M:%S")
        except (TypeError, ValueError):
            timestamp = "--:--:--"

        item = QListWidgetItem(f"{timestamp}  {symbol}  {title}{EVENT_SEPARATOR}{message}")
        item.setForeground(QBrush(QColor(color)))
        item.setFont(QFont("Consolas", 9))
        item.setToolTip(f"{title}\n{message}")
        self.feed.addItem(item)
        while self.feed.count() > 80:
            self.feed.takeItem(0)
        self.feed.scrollToBottom()
        self.refresh()
