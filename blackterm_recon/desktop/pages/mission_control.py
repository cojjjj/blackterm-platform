from __future__ import annotations

from collections import deque
from datetime import datetime
from importlib.metadata import PackageNotFoundError, version

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
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...events import EventLevel
from ..widgets import MetricCard, PulseDot, Sparkline, ThreatMeter, TypingLabel
from ..system_telemetry import SystemTelemetryPanel


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
    new_investigation_requested = Signal()
    live_scan_requested = Signal()
    cases_requested = Signal()
    reports_requested = Signal()
    osint_requested = Signal()
    threat_intelligence_requested = Signal()

    def __init__(self, engine, event_bus, event_store):
        super().__init__()
        self.engine = engine
        self.event_bus = event_bus
        self.event_store = event_store
        self.running_scans = 0
        self.recent_levels = deque(maxlen=50)
        self.scan_phase = 0
        self.started_at = datetime.now().astimezone()
        self.current_target = ""
        self.operation_started_at = None
        self.operation_stage = "IDLE"
        self.workflow_active = False
        try:
            self.platform_version = version("blackterm-recon")
        except PackageNotFoundError:
            self.platform_version = "9.1.0"

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
        self.release_badge = QLabel(f"v{self.platform_version}  •  INTELLIGENCE RELEASE")
        self.release_badge.setObjectName("releaseBadge")
        self.release_badge.setStyleSheet(
            "QLabel#releaseBadge {"
            " color: #31b7ff; background: rgba(49, 183, 255, 18);"
            " border: 1px solid #24557a; border-radius: 8px;"
            " padding: 6px 10px; font-weight: 700; letter-spacing: 1px;"
            " }"
        )
        top.addWidget(self.release_badge)
        root.addLayout(top)

        metrics = QHBoxLayout()
        metrics.setSpacing(8)
        self.scans = MetricCard("Recon Operations", "0", "Saved authorized scans")
        self.cases = MetricCard("Cases", "0", "Investigation workspaces")
        self.open_cases = MetricCard("Active Cases", "0", "Open, active, or review")
        self.open_ports = MetricCard("Open Ports", "0", "Across saved scans")
        self.alerts = MetricCard("Alerts", "0", "Warnings and errors")
        for card in (self.scans, self.cases, self.open_cases, self.open_ports, self.alerts):
            metrics.addWidget(card)
        root.addLayout(metrics)

        # Compact live-operation strip. It remains visible while idle so Mission
        # Control always communicates what the automation pipeline will do next.
        operation_panel = QFrame()
        operation_panel.setObjectName("panel")
        operation_layout = QHBoxLayout(operation_panel)
        operation_layout.setContentsMargins(10, 8, 10, 8)
        operation_layout.setSpacing(10)
        operation_title_box = QVBoxLayout()
        operation_title_box.setSpacing(1)
        operation_title_box.addWidget(QLabel("ACTIVE OPERATION"))
        self.operation_target = QLabel("Awaiting operation — select New Investigation to begin")
        self.operation_target.setObjectName("muted")
        operation_title_box.addWidget(self.operation_target)
        operation_layout.addLayout(operation_title_box, 2)

        self.operation_bars = {}
        for stage in ("RECON", "OSINT", "THREAT INTEL", "AI CORRELATION", "REPORT"):
            stage_box = QVBoxLayout()
            stage_box.setSpacing(2)
            stage_label = QLabel(stage)
            stage_label.setObjectName("muted")
            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setValue(0)
            bar.setTextVisible(False)
            bar.setMaximumHeight(8)
            stage_box.addWidget(stage_label)
            stage_box.addWidget(bar)
            operation_layout.addLayout(stage_box, 1)
            self.operation_bars[stage] = bar

        self.operation_elapsed = QLabel("IDLE")
        self.operation_elapsed.setObjectName("statusActive")
        self.operation_elapsed.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        operation_layout.addWidget(self.operation_elapsed)
        root.addWidget(operation_panel)

        body = QGridLayout()
        body.setHorizontalSpacing(8)
        body.setVerticalSpacing(8)
        body.setColumnStretch(0, 3)
        body.setColumnStretch(1, 2)
        body.setColumnStretch(2, 2)

        activity_panel = QFrame()
        activity_panel.setObjectName("panel")
        activity_layout = QVBoxLayout(activity_panel)
        activity_layout.setContentsMargins(10, 10, 10, 10)
        activity_layout.addWidget(QLabel("RECENT PLATFORM ACTIVITY"))
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
        activity_layout.addWidget(self.feed)

        quick_panel = QFrame()
        quick_panel.setObjectName("panel")
        quick_layout = QVBoxLayout(quick_panel)
        quick_layout.addWidget(QLabel("QUICK ACTIONS"))
        quick_layout.addWidget(self._action_button("NEW INVESTIGATION", self.new_investigation_requested.emit, primary=True))
        quick_layout.addWidget(self._action_button("OPEN LIVE SCAN", self.live_scan_requested.emit))
        quick_layout.addWidget(self._action_button("COLLECT OSINT", self.osint_requested.emit))
        quick_layout.addWidget(self._action_button("ANALYZE THREAT", self.threat_intelligence_requested.emit))
        quick_layout.addWidget(self._action_button("OPEN CASES", self.cases_requested.emit))
        quick_layout.addWidget(self._action_button("OPEN REPORTS", self.reports_requested.emit))
        quick_layout.addStretch()

        status_panel = QFrame()
        status_panel.setObjectName("panel")
        status_layout = QVBoxLayout(status_panel)
        status_layout.addWidget(QLabel("PLATFORM STATUS"))
        self.module_status = QLabel()
        self.module_status.setWordWrap(True)
        self.module_status.setObjectName("muted")
        status_layout.addWidget(self.module_status)
        status_layout.addWidget(QLabel("PLATFORM LOAD"))
        self.load = QProgressBar()
        self.load.setRange(0, 100)
        status_layout.addWidget(self.load)
        self.threat_meter = ThreatMeter()
        status_layout.addWidget(self.threat_meter)
        self.system_telemetry = SystemTelemetryPanel()
        status_layout.addWidget(self.system_telemetry)
        status_layout.addStretch()

        analyst_panel = QFrame()
        analyst_panel.setObjectName("panel")
        analyst_layout = QVBoxLayout(analyst_panel)
        analyst_layout.addWidget(QLabel("AI OPERATIONS ANALYST"))
        self.ai_state = QLabel("STANDBY")
        self.ai_state.setObjectName("statusActive")
        self.ai_detail = TypingLabel(
            "Mission Control is monitoring reconnaissance, OSINT, threat intelligence, cases, and platform events.",
            interval=10,
        )
        self.ai_detail.setWordWrap(True)
        self.ai_detail.setObjectName("muted")
        self.ai_score = QProgressBar()
        self.ai_score.setRange(0, 100)
        self.ai_score.setValue(0)
        self.ai_score.setFormat("CONTEXT SCORE %p%")
        analyst_layout.addWidget(self.ai_state)
        analyst_layout.addWidget(self.ai_detail)
        analyst_layout.addWidget(self.ai_score)
        analyst_layout.addStretch()

        trend_panel = QFrame()
        trend_panel.setObjectName("panel")
        trend_layout = QVBoxLayout(trend_panel)
        trend_layout.addWidget(QLabel("EVENT ACTIVITY"))
        self.sparkline = Sparkline()
        trend_layout.addWidget(self.sparkline)
        self.threat = QLabel()
        self.threat.setWordWrap(True)
        self.threat.setObjectName("muted")
        trend_layout.addWidget(self.threat)

        timeline_panel = QFrame()
        timeline_panel.setObjectName("panel")
        timeline_layout = QVBoxLayout(timeline_panel)
        timeline_layout.addWidget(QLabel("OPERATION TIMELINE"))
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

        body.addWidget(activity_panel, 0, 0, 3, 1)
        body.addWidget(quick_panel, 0, 1, 2, 1)
        body.addWidget(status_panel, 0, 2, 1, 1)
        body.addWidget(analyst_panel, 1, 2, 1, 1)
        body.addWidget(trend_panel, 2, 1, 1, 1)
        body.addWidget(timeline_panel, 2, 2, 1, 1)
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

    def _action_button(self, text, callback, primary=False):
        button = QPushButton(text)
        if primary:
            button.setObjectName("primaryButton")
            button.setStyleSheet(
                "QPushButton#primaryButton {"
                " color: #020812; font-weight: 800;"
                " border: 1px solid #47f0cf; border-radius: 8px;"
                " background: qlineargradient(x1:0, y1:0, x2:1, y2:0,"
                " stop:0 #31b7ff, stop:1 #35dfb0);"
                " padding: 8px 12px;"
                " }"
                "QPushButton#primaryButton:hover {"
                " border-color: #ffffff;"
                " background: qlineargradient(x1:0, y1:0, x2:1, y2:0,"
                " stop:0 #66cbff, stop:1 #5ff2c9);"
                " }"
                "QPushButton#primaryButton:pressed { padding-top: 9px; }"
            )
        button.clicked.connect(callback)
        button.setMinimumHeight(38)
        return button

    def animate_scan_state(self):
        if not self.running_scans:
            self.scan_timer.stop()
            self.state.setText("PLATFORM ONLINE")
            return
        self.scan_phase = (self.scan_phase + 1) % 4
        self.state.setText("SCANNING" + "." * self.scan_phase)

    def refresh(self):
        scan_stats = self.engine.repository.stats()
        event_stats = self.event_store.stats() if self.event_store else {
            "warnings": 0, "errors": 0, "total": 0, "completed_scans": 0, "ai": 0
        }
        cases = self.engine.repository.list_cases()
        active_cases = sum(1 for case in cases if case.get("status", "OPEN") != "CLOSED")

        self.scans.set_value(scan_stats["scans"])
        self.cases.set_value(len(cases))
        self.open_cases.set_value(active_cases)
        self.open_ports.set_value(scan_stats["open_ports"])
        self.alerts.set_value(event_stats["warnings"] + event_stats["errors"])

        recent_counts = self.event_store.recent_counts() if self.event_store else [0]
        self.sparkline.set_values(recent_counts or [0])
        load_value = min(
            100,
            int(event_stats["warnings"] * 3 + event_stats["errors"] * 7 + self.running_scans * 15),
        )
        self.load.setValue(load_value)
        # Mission Control represents current operational risk, not the raw lifetime
        # count of warnings.  Normalize alerts against total recorded events and
        # cap passive exposure so an established workspace does not permanently
        # display CRITICAL simply because it has accumulated history.
        warning_count = max(0, int(event_stats.get("warnings", 0)))
        error_count = max(0, int(event_stats.get("errors", 0)))
        total_events = max(1, int(event_stats.get("total", 0)), warning_count + error_count)
        warning_rate = warning_count / total_events
        error_rate = error_count / total_events

        exposure_component = min(25.0, max(0, scan_stats["open_ports"]) * 0.5)
        warning_component = min(20.0, warning_rate * 20.0)
        error_component = min(45.0, error_rate * 55.0)
        active_operation_component = min(10.0, self.running_scans * 10.0)
        threat_score = round(
            min(
                100.0,
                exposure_component
                + warning_component
                + error_component
                + active_operation_component,
            )
        )
        self.threat_meter.set_value(threat_score)

        # Context score measures how much telemetry is available to the analyst;
        # it is intentionally separate from threat severity.
        context_score = min(
            100,
            35
            + min(25, scan_stats["scans"] * 2)
            + min(20, len(cases))
            + min(20, event_stats.get("ai", 0) * 2),
        )
        self.ai_score.setValue(context_score)

        if threat_score <= 24:
            level = "LOW"
        elif threat_score <= 49:
            level = "GUARDED"
        elif threat_score <= 74:
            level = "ELEVATED"
        else:
            level = "CRITICAL"

        if error_count:
            context = (
                f"{error_count} error event(s) and {warning_count} warning event(s) "
                "are present in recorded telemetry."
            )
        elif warning_count:
            context = (
                f"{warning_count} warning event(s) are recorded; severity is "
                "normalized against overall platform activity."
            )
        else:
            context = "No warning or error events are currently recorded."

        self.threat.setText(
            f"CONTEXT: {level}\n{context}\n\n"
            f"Completed scans: {event_stats['completed_scans']}\n"
            f"AI events: {event_stats['ai']}\n"
            f"Last scan: {scan_stats['last_scan']}"
        )
        now = datetime.now().astimezone()
        uptime_seconds = max(0, int((now - self.started_at).total_seconds()))
        uptime_hours, remainder = divmod(uptime_seconds, 3600)
        uptime_minutes, uptime_seconds = divmod(remainder, 60)
        uptime_text = f"{uptime_hours:02d}h {uptime_minutes:02d}m {uptime_seconds:02d}s"
        self.module_status.setText(
            "● Recon Engine          ONLINE\n"
            "● OSINT Engine          READY\n"
            "● Threat Intelligence   READY\n"
            "● Case Database         CONNECTED\n"
            "● Reporting             READY\n\n"
            f"Uptime:              {uptime_text}\n"
            f"Last refresh:        {now.strftime('%H:%M:%S')}\n"
            f"Running operations:  {self.running_scans}\n"
            f"Persistent events:   {event_stats['total']}"
        )

        threat_colors = {
            "LOW": "#35df83",
            "GUARDED": "#ffd166",
            "ELEVATED": "#ff9f43",
            "CRITICAL": "#ff5c7a",
        }
        self.threat.setStyleSheet(f"color: {threat_colors[level]};")

        if self.operation_started_at:
            elapsed = max(0, int((now - self.operation_started_at).total_seconds()))
            minutes, seconds = divmod(elapsed, 60)
            self.operation_elapsed.setText(f"{minutes:02d}:{seconds:02d}")
        else:
            self.operation_elapsed.setText("READY")

        if self.feed.count() == 0:
            rows = self.engine.repository.list_recent(8)
            for row in reversed(rows):
                item = QListWidgetItem(
                    f"SCAN #{row['id']}  {row['target']}  —  {row['open_ports']} open port(s)"
                )
                item.setForeground(QBrush(QColor("#31b7ff")))
                self.feed.addItem(item)
            for case in reversed(cases[:5]):
                item = QListWidgetItem(
                    f"CASE #{case['id']}  {case['name']}  —  {case['status']}"
                )
                item.setForeground(QBrush(QColor("#35df83")))
                self.feed.addItem(item)
            if self.feed.count() == 0:
                self.feed.addItem("No platform activity recorded yet.")

    def _set_operation_stage(self, stage: str, target: str = ""):
        order = ("RECON", "OSINT", "THREAT INTEL", "AI CORRELATION", "REPORT")
        if target:
            self.current_target = target
        if self.current_target:
            self.operation_target.setText(self.current_target)
        self.operation_stage = stage
        if stage in order and self.operation_started_at is None:
            self.operation_started_at = datetime.now().astimezone()
        for name, bar in self.operation_bars.items():
            if stage == "COMPLETE":
                value = 100
            elif stage in order:
                current = order.index(stage)
                index = order.index(name)
                value = 100 if index < current else (55 if index == current else 0)
            else:
                value = 0
            bar.setValue(value)
        if stage == "COMPLETE":
            self.operation_elapsed.setText("COMPLETE")
            self.operation_target.setText(
                f"{self.current_target or 'Operation'} — workflow complete"
            )


    def set_workflow_progress(self, stage: str, percent: int, message: str, metadata: dict | None = None):
        self.workflow_active = True
        stage_map = {
            "recon": "RECON",
            "osint": "OSINT",
            "threat": "THREAT INTEL",
            "correlation": "AI CORRELATION",
            "report": "REPORT",
        }
        label = stage_map.get(str(stage).lower())
        metadata = metadata or {}
        target = str(metadata.get("target") or self.current_target or "")
        if label:
            self._set_operation_stage(label, target)
            self.operation_bars[label].setValue(max(0, min(100, int(percent))))
        self._set_contextual_analyst(
            "AUTONOMOUS WORKFLOW",
            message,
        )

    def complete_workflow(self, target: str = ""):
        self.workflow_active = False
        self._set_operation_stage("COMPLETE", target)
        self.operation_elapsed.setText("COMPLETE")
        self._set_contextual_analyst(
            "INVESTIGATION READY",
            "The autonomous workflow completed and the case is ready for analyst review.",
        )

    def fail_workflow(self, message: str):
        self.workflow_active = False
        self.operation_elapsed.setText("REVIEW")
        self._set_contextual_analyst("WORKFLOW REQUIRES REVIEW", message)

    def _set_contextual_analyst(self, state: str, detail: str):
        self.ai_state.setText(state)
        self.ai_detail.set_typed_text(detail)

    def on_event(self, event):
        title_lower = (event.title or "").lower()
        category_lower = (event.category or "").lower()
        module_lower = (event.module or "").lower()
        metadata = event.metadata or {}
        target = str(metadata.get("target") or metadata.get("indicator") or "")

        if event.title == "Scan Started":
            self.running_scans += 1
            self._set_operation_stage("RECON", target)
            self._set_contextual_analyst("ANALYZING TARGET", event.message)
            self.scan_timer.start()
        elif event.title == "Open Port Observed":
            port = metadata.get("port", "?")
            service = metadata.get("service", "unknown")
            self._set_contextual_analyst(
                "CORRELATING SERVICES",
                f"Observed {service} on TCP/{port}. Evaluating exposure context and service risk.",
            )
        elif "osint" in title_lower or "osint" in category_lower or "osint" in module_lower:
            self._set_operation_stage("OSINT", target)
            self._set_contextual_analyst("ENRICHING PUBLIC SOURCES", event.message)
        elif "threat" in title_lower or "threat" in category_lower or "threat" in module_lower:
            self._set_operation_stage("THREAT INTEL", target)
            self._set_contextual_analyst("CORRELATING THREAT INTELLIGENCE", event.message)
        elif event.level == EventLevel.AI:
            self._set_operation_stage("AI CORRELATION", target)
            self._set_contextual_analyst("ANALYSIS READY", event.message)
        elif "report" in title_lower or "report" in category_lower or "report" in module_lower:
            self._set_operation_stage("REPORT", target)
            self._set_contextual_analyst("GENERATING REPORT", event.message)
        elif event.title == "Investigation Complete":
            self.complete_workflow(target)
        elif event.title == "Investigation Failed":
            self.fail_workflow(event.message)
        elif event.title == "Scan Complete":
            self.running_scans = max(0, self.running_scans - 1)
            # A standalone scan is complete here. Autonomous workflows continue
            # into OSINT, threat intelligence, correlation, and reporting.
            if not self.workflow_active and metadata.get("workflow") != "autonomous":
                self._set_operation_stage("COMPLETE", target)
                self._set_contextual_analyst("SCAN REVIEW COMPLETE", event.message)
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
