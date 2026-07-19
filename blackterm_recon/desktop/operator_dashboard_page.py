from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QPointF, QTimer, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..operator_dashboard import build_operator_stats
from .live_widgets import AnimatedNumberLabel
from .living_interface import LoadingStrip, PulseController


ACCENT_BLUE = "#31b7ff"
ACCENT_PURPLE = "#b000ff"
ACCENT_GREEN = "#36e6b0"
ACCENT_AMBER = "#f0b85a"
ACCENT_RED = "#ff5c7a"
TEXT_MUTED = "#8fa4bd"


class MiniSparkline(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.values = [0, 0, 0, 0, 0, 0, 0]
        self.setMinimumHeight(32)
        self.setMaximumHeight(34)

    def set_values(self, values):
        cleaned = [max(0, int(v)) for v in values][-12:]
        self.values = cleaned or [0]
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(4, 5, -4, -5)
        if len(self.values) < 2:
            return
        low = min(self.values)
        high = max(self.values)
        spread = max(1, high - low)
        path = QPainterPath()
        for index, value in enumerate(self.values):
            x = rect.left() + rect.width() * index / (len(self.values) - 1)
            y = rect.bottom() - rect.height() * (value - low) / spread
            if index == 0:
                path.moveTo(x, y)
            else:
                path.lineTo(x, y)
        painter.setPen(QPen(QColor(ACCENT_PURPLE), 2.0))
        painter.drawPath(path)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(ACCENT_BLUE))
        last_x = rect.right()
        last_y = rect.bottom() - rect.height() * (self.values[-1] - low) / spread
        painter.drawEllipse(QPointF(last_x, last_y), 3.5, 3.5)


class MetricCard(QFrame):
    def __init__(self, label: str, subtitle: str, accent: str, parent=None):
        super().__init__(parent)
        self.accent = accent
        self.setObjectName("operatorMetricCard")
        self.setMinimumHeight(112)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setStyleSheet(
            f"""
            QFrame#operatorMetricCard {{
                background: #0d0a15;
                border: 1px solid #233e5f;
                border-left: 4px solid {accent};
                border-radius: 12px;
            }}
            QFrame#operatorMetricCard:hover {{
                background: #11101c;
                border-color: {accent};
            }}
            """
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 12, 15, 10)
        layout.setSpacing(3)

        top = QHBoxLayout()
        self.label = QLabel(label)
        self.label.setStyleSheet(
            "font-size:10px;font-weight:800;color:#9fb1c7;letter-spacing:0.6px;"
        )
        self.state_dot = QLabel("●")
        self.state_dot.setStyleSheet(f"color:{accent};font-size:10px;")
        top.addWidget(self.label)
        top.addStretch()
        top.addWidget(self.state_dot)
        layout.addLayout(top)

        self.value = AnimatedNumberLabel(0)
        self.value.setStyleSheet(
            f"font-size:28px;font-weight:900;color:{accent};"
        )
        layout.addWidget(self.value)

        self.subtitle = QLabel(subtitle)
        self.subtitle.setStyleSheet(
            "font-size:10px;color:#7f93ac;"
        )
        layout.addWidget(self.subtitle)

        self.sparkline = MiniSparkline()
        layout.addWidget(self.sparkline)

    def set_value(self, value: int, *, animate: bool = True):
        self.value.set_value(value, animate=animate)

    def set_history(self, values):
        self.sparkline.set_values(values)

    def set_accent(self, accent: str):
        self.accent = accent
        self.state_dot.setStyleSheet(f"color:{accent};font-size:10px;")
        self.value.setStyleSheet(f"font-size:28px;font-weight:900;color:{accent};")
        self.setStyleSheet(
            f"""
            QFrame#operatorMetricCard {{
                background: #0d0a15;
                border: 1px solid #233e5f;
                border-left: 4px solid {accent};
                border-radius: 12px;
            }}
            QFrame#operatorMetricCard:hover {{
                background: #11101c;
                border-color: {accent};
            }}
            """
        )


class StatusPill(QLabel):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumWidth(92)
        self.setStyleSheet(
            "padding:5px 10px;border-radius:10px;"
            "background:#11263a;color:#36e6b0;font-weight:800;font-size:10px;"
        )

    def set_status(self, text: str):
        value = text.upper()
        if value in {"ACTIVE", "OPEN"}:
            bg, fg = "#102c2a", ACCENT_GREEN
        elif value == "REVIEW":
            bg, fg = "#342812", ACCENT_AMBER
        elif value == "CLOSED":
            bg, fg = "#1b2230", "#8ea0b6"
        else:
            bg, fg = "#25152d", "#d08cff"
        self.setText(value)
        self.setStyleSheet(
            f"padding:5px 10px;border-radius:10px;"
            f"background:{bg};color:{fg};font-weight:800;font-size:10px;"
        )


class OperatorDashboardPage(QWidget):
    open_case_requested = Signal(int)
    live_investigation_requested = Signal()
    mission_control_requested = Signal()

    def __init__(self, engine, event_bus=None, operator: str = "TYLER", parent=None):
        super().__init__(parent)
        self.engine = engine
        self.event_bus = event_bus
        self.operator = operator
        self.current_stats = None
        self._resume_case_id = None

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 8, 10, 8)
        root.setSpacing(10)

        hero = QFrame()
        hero.setObjectName("operatorHero")
        hero.setStyleSheet(
            """
            QFrame#operatorHero {
                background: qlineargradient(
                    x1:0,y1:0,x2:1,y2:0,
                    stop:0 #0b1422,
                    stop:0.55 #100c1a,
                    stop:1 #171025
                );
                border: 1px solid #29476b;
                border-radius: 14px;
            }
            """
        )
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(20, 16, 18, 16)

        identity = QVBoxLayout()
        self.greeting = QLabel("OPERATOR DASHBOARD")
        self.greeting.setStyleSheet(
            "font-size:26px;font-weight:900;color:#ffffff;"
        )
        self.identity = QLabel("OPERATOR // TYLER")
        self.identity.setStyleSheet(
            f"font-family:Consolas;font-size:11px;font-weight:800;color:{ACCENT_BLUE};"
        )
        self.shift = QLabel("")
        self.shift.setStyleSheet(
            "font-size:10px;color:#8fa4bd;"
        )
        identity.addWidget(self.greeting)
        identity.addWidget(self.identity)
        identity.addWidget(self.shift)
        hero_layout.addLayout(identity)
        hero_layout.addStretch()

        self.system_status = StatusPill("PLATFORM ONLINE")
        self.system_status.setMinimumWidth(130)
        hero_layout.addWidget(self.system_status)

        mission = QPushButton("MISSION CONTROL")
        mission.clicked.connect(self.mission_control_requested.emit)
        live = QPushButton("START LIVE INVESTIGATION")
        live.setObjectName("primary")
        live.clicked.connect(self.live_investigation_requested.emit)
        refresh = QPushButton("REFRESH")
        refresh.clicked.connect(self.refresh)
        hero_layout.addWidget(mission)
        hero_layout.addWidget(live)
        hero_layout.addWidget(refresh)
        root.addWidget(hero)
        self.status_pulse = PulseController(self.system_status, 0.76, 1.0)

        self.loading_strip = LoadingStrip()
        self.loading_strip.completed.connect(self._complete_resume)
        root.addWidget(self.loading_strip)

        metrics = QGridLayout()
        metrics.setHorizontalSpacing(8)
        metrics.setVerticalSpacing(8)

        self.total_cases = MetricCard(
            "INVESTIGATIONS", "All saved cases", ACCENT_BLUE
        )
        self.active_cases = MetricCard(
            "ACTIVE CASES", "Open workflow", ACCENT_GREEN
        )
        self.evidence = MetricCard(
            "EVIDENCE", "Preserved artifacts", "#55d6be"
        )
        self.relationships = MetricCard(
            "RELATIONSHIPS", "Correlated links", ACCENT_PURPLE
        )
        self.high_priority = MetricCard(
            "HIGH PRIORITY", "Requires review", ACCENT_GREEN
        )
        self.today_activity = MetricCard(
            "TODAY'S ACTIVITY", "Timeline events", ACCENT_AMBER
        )

        cards = (
            self.total_cases,
            self.active_cases,
            self.evidence,
            self.relationships,
            self.high_priority,
            self.today_activity,
        )
        for index, card in enumerate(cards):
            metrics.addWidget(card, index // 3, index % 3)
        root.addLayout(metrics)

        middle = QHBoxLayout()
        middle.setSpacing(8)

        resume = QFrame()
        resume.setObjectName("operatorResume")
        resume.setStyleSheet(
            """
            QFrame#operatorResume {
                background:#0d0a15;
                border:1px solid #2a4a70;
                border-radius:12px;
            }
            """
        )
        resume_layout = QVBoxLayout(resume)
        resume_layout.setContentsMargins(16, 13, 16, 12)

        title_row = QHBoxLayout()
        title = QLabel("CONTINUE INVESTIGATION")
        title.setStyleSheet(
            "font-size:10px;font-weight:800;color:#a9b9cc;letter-spacing:0.6px;"
        )
        self.last_status = StatusPill("READY")
        title_row.addWidget(title)
        title_row.addStretch()
        title_row.addWidget(self.last_status)
        resume_layout.addLayout(title_row)

        self.last_case_title = QLabel("No investigation available")
        self.last_case_title.setWordWrap(True)
        self.last_case_title.setStyleSheet(
            "font-size:16px;font-weight:900;color:#f3f8ff;"
        )
        self.last_case_meta = QLabel("")
        self.last_case_meta.setWordWrap(True)
        self.last_case_meta.setStyleSheet(
            "font-family:Consolas;font-size:10px;color:#91a6bf;"
        )
        self.resume_button = QPushButton("RESUME CASE")
        self.resume_button.setObjectName("primary")
        self.resume_button.setEnabled(False)
        self.resume_button.clicked.connect(self.resume_last_case)

        resume_layout.addWidget(self.last_case_title)
        resume_layout.addWidget(self.last_case_meta)
        resume_layout.addStretch()
        resume_layout.addWidget(self.resume_button)
        middle.addWidget(resume, 1)

        awareness = QFrame()
        awareness.setObjectName("operatorAwareness")
        awareness.setStyleSheet(
            """
            QFrame#operatorAwareness {
                background:#0d0a15;
                border:1px solid #2a4a70;
                border-radius:12px;
            }
            """
        )
        awareness_layout = QVBoxLayout(awareness)
        awareness_layout.setContentsMargins(16, 13, 16, 12)
        awareness_layout.addWidget(QLabel("OPERATOR AWARENESS"))

        self.awareness_title = QLabel("PLATFORM READY")
        self.awareness_title.setStyleSheet(
            f"font-size:16px;font-weight:900;color:{ACCENT_GREEN};"
        )
        self.awareness_text = QLabel(
            "BLACKTERM is ready to continue the current investigation workflow."
        )
        self.awareness_text.setWordWrap(True)
        self.awareness_text.setStyleSheet(
            "font-size:11px;color:#b3c1d1;"
        )
        self.load = QProgressBar()
        self.load.setRange(0, 100)
        self.load.setValue(0)
        self.load.setTextVisible(True)
        self.load.setFormat("OPERATIONAL LOAD // %p%")
        awareness_layout.addWidget(self.awareness_title)
        awareness_layout.addWidget(self.awareness_text)
        awareness_layout.addStretch()
        awareness_layout.addWidget(self.load)
        middle.addWidget(awareness, 1)
        root.addLayout(middle)

        recent = QFrame()
        recent.setObjectName("operatorRecent")
        recent.setStyleSheet(
            """
            QFrame#operatorRecent {
                background:#0d0a15;
                border:1px solid #2a4a70;
                border-radius:12px;
            }
            """
        )
        recent_layout = QVBoxLayout(recent)
        recent_layout.setContentsMargins(12, 10, 12, 10)

        recent_header = QHBoxLayout()
        recent_title = QLabel("RECENT INVESTIGATIONS")
        recent_title.setStyleSheet(
            "font-size:11px;font-weight:900;color:#f3f8ff;"
        )
        recent_header.addWidget(recent_title)
        recent_header.addStretch()
        self.clock = QLabel("")
        self.clock.setStyleSheet(
            "font-family:Consolas;font-size:10px;color:#8fa4bd;"
        )
        recent_header.addWidget(self.clock)
        recent_layout.addLayout(recent_header)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["ID", "CASE", "STATUS", "SCANS", "CREATED"]
        )
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)
        self.table.doubleClicked.connect(self.open_selected_case)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setColumnWidth(0, 55)
        self.table.setColumnWidth(1, 390)
        self.table.setColumnWidth(2, 105)
        self.table.setColumnWidth(3, 75)
        self.table.setStyleSheet(
            """
            QTableWidget {
                background:#090711;
                alternate-background-color:#0e0b17;
                border:1px solid #203d5c;
                border-radius:8px;
                gridline-color:transparent;
                selection-background-color:#173c5d;
                selection-color:#ffffff;
            }
            QHeaderView::section {
                background:#101d2d;
                color:#f4f8ff;
                border:none;
                border-bottom:1px solid #31577f;
                padding:8px;
                font-size:10px;
                font-weight:800;
            }
            QTableWidget::item {
                padding:8px;
                border-bottom:1px solid #172b41;
            }
            """
        )
        recent_layout.addWidget(self.table, 1)

        row = QHBoxLayout()
        self.open_selected = QPushButton("OPEN SELECTED CASE")
        self.open_selected.clicked.connect(self.open_selected_case)
        row.addWidget(self.open_selected)
        row.addStretch()
        recent_layout.addLayout(row)
        root.addWidget(recent, 1)

        self.clock_timer = QTimer(self)
        self.clock_timer.setInterval(1000)
        self.clock_timer.timeout.connect(self.update_clock)
        self.clock_timer.start()

        self.auto_refresh = QTimer(self)
        self.auto_refresh.setInterval(12000)
        self.auto_refresh.timeout.connect(self.refresh)
        self.auto_refresh.start()

        self.update_clock()
        self.refresh(animate=False)

    def update_clock(self):
        self.clock.setText(datetime.now().strftime("%A // %B %d // %H:%M:%S"))

    def refresh(self, checked=False, *, animate=True):
        stats = build_operator_stats(self.engine.repository, self.operator)
        self.current_stats = stats

        self.greeting.setText(stats.greeting)
        self.identity.setText(f"OPERATOR // {stats.operator}")
        self.shift.setText(
            f"BLACKTERM INTELLIGENCE PLATFORM // "
            f"{stats.active_cases} ACTIVE // {stats.today_activity} EVENTS TODAY"
        )
        self.system_status.set_status("ONLINE")

        self.total_cases.set_value(stats.total_cases, animate=animate)
        self.active_cases.set_value(stats.active_cases, animate=animate)
        self.evidence.set_value(stats.evidence_items, animate=animate)
        self.relationships.set_value(stats.relationships, animate=animate)
        self.high_priority.set_value(stats.high_priority_cases, animate=animate)
        self.today_activity.set_value(stats.today_activity, animate=animate)

        # Lightweight trend visuals based on current totals.
        self.total_cases.set_history([max(0, stats.total_cases - i) for i in [6, 5, 4, 3, 2, 1, 0]])
        self.active_cases.set_history([max(0, stats.active_cases - 1), stats.active_cases] * 4)
        self.evidence.set_history([max(0, stats.evidence_items - step) for step in [18, 14, 10, 7, 4, 2, 0]])
        self.relationships.set_history([max(0, stats.relationships - step) for step in [35, 28, 20, 14, 9, 4, 0]])
        self.high_priority.set_history([0, 0, 0, stats.high_priority_cases, stats.high_priority_cases])
        self.today_activity.set_history([max(0, stats.today_activity - step) for step in [40, 30, 20, 12, 7, 3, 0]])

        if stats.high_priority_cases >= 5:
            self.high_priority.set_accent(ACCENT_RED)
        elif stats.high_priority_cases > 0:
            self.high_priority.set_accent(ACCENT_AMBER)
        else:
            self.high_priority.set_accent(ACCENT_GREEN)

        if stats.last_case_id is not None:
            self.last_case_title.setText(
                f"CASE #{stats.last_case_id} // {stats.last_case_name}"
            )
            self.last_status.set_status(stats.last_case_status)
            self.last_case_meta.setText(
                f"CREATED // {stats.last_case_created[:19] or 'UNKNOWN'}\n"
                "Resume directly into the Investigation Workspace with full evidence, "
                "timeline, graph, correlation, and AI context preserved."
            )
            self.resume_button.setEnabled(True)
        else:
            self.last_case_title.setText("No investigation available")
            self.last_status.set_status("READY")
            self.last_case_meta.setText(
                "Start Live Investigation to create the first case."
            )
            self.resume_button.setEnabled(False)

        if stats.high_priority_cases:
            self.awareness_title.setText("HIGH-PRIORITY REVIEW REQUIRED")
            self.awareness_title.setStyleSheet(
                f"font-size:16px;font-weight:900;color:{ACCENT_AMBER};"
            )
            self.awareness_text.setText(
                f"{stats.high_priority_cases} investigation(s) contain high-priority "
                "correlated context. Validate evidence and recommendations before closure."
            )
        elif stats.active_cases:
            self.awareness_title.setText("ACTIVE INVESTIGATIONS")
            self.awareness_title.setStyleSheet(
                f"font-size:16px;font-weight:900;color:{ACCENT_BLUE};"
            )
            self.awareness_text.setText(
                f"{stats.active_cases} case(s) remain open or under review. "
                "Continue the latest investigation or launch fresh intelligence."
            )
        else:
            self.awareness_title.setText("PLATFORM READY")
            self.awareness_title.setStyleSheet(
                f"font-size:16px;font-weight:900;color:{ACCENT_GREEN};"
            )
            self.awareness_text.setText(
                "No active cases require attention. BLACKTERM is ready for a new investigation."
            )

        platform_load = min(
            100,
            stats.active_cases * 9
            + stats.high_priority_cases * 18
            + min(28, stats.today_activity // 2),
        )
        self.load.setValue(platform_load)

        self.table.setRowCount(len(stats.recent_cases))
        for row, case in enumerate(stats.recent_cases):
            values = [
                case.get("id", ""),
                case.get("name", ""),
                case.get("status", ""),
                case.get("scan_count", 0),
                str(case.get("created_at", ""))[:19],
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if column == 2:
                    status = str(value).upper()
                    if status in {"ACTIVE", "OPEN"}:
                        item.setForeground(QColor(ACCENT_GREEN))
                    elif status == "REVIEW":
                        item.setForeground(QColor(ACCENT_AMBER))
                    elif status == "CLOSED":
                        item.setForeground(QColor("#8ea0b6"))
                self.table.setItem(row, column, item)

        if self.table.rowCount():
            self.table.selectRow(0)

    def selected_case_id(self):
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return None
        item = self.table.item(rows[0].row(), 0)
        return int(item.text()) if item else None

    def resume_last_case(self):
        if self.current_stats and self.current_stats.last_case_id is not None:
            self._resume_case_id = self.current_stats.last_case_id
            self.resume_button.setEnabled(False)
            self.resume_button.setText("LOADING INVESTIGATION...")
            self.loading_strip.play(
                "Restoring evidence, timeline, graph, and AI context",
                720,
            )

    def _complete_resume(self):
        if self._resume_case_id is not None:
            case_id = self._resume_case_id
            self._resume_case_id = None
            self.resume_button.setText("RESUME CASE")
            self.resume_button.setEnabled(True)
            self.open_case_requested.emit(case_id)

    def open_selected_case(self, *_):
        case_id = self.selected_case_id()
        if case_id is not None:
            self.open_case_requested.emit(case_id)
