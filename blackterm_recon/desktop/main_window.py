from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QEvent, QPropertyAnimation
from PySide6.QtWidgets import QHBoxLayout, QMainWindow, QStackedWidget, QVBoxLayout, QWidget

from .command_bar import CommandBar
from .dock import Dock
from .event_feed import EventFeedPage, Toast
from .pages.assistant import AssistantPage
from .pages.cases import CasesPage
from .pages.dashboard import DashboardPage
from .pages.history import HistoryPage
from .pages.mission_control import MissionControlPage
from .pages.network import NetworkPage
from .pages.platform import PlatformPage
from .pages.plugins import PluginsPage
from .pages.reports import ReportsPage
from .pages.scan import ScanPage
from .pages.settings import SettingsPage
from .pages.terminal import TerminalPage
from .theme import stylesheet
from .widgets import ParticleField


class MainWindow(QMainWindow):
    def __init__(self, engine, operator="OPERATOR", event_bus=None, event_store=None):
        super().__init__()
        self.engine = engine
        self.operator = operator
        self.event_bus = event_bus
        self.event_store = event_store
        self.setWindowTitle("BLACKTERM Platform v6.0 // Living Platform")
        self.resize(1540, 920)
        self.setMinimumSize(1160, 740)
        self.setMouseTracking(True)

        root_widget = QWidget()
        root_widget.setObjectName("rootWindow")
        self.setCentralWidget(root_widget)
        self.particles = ParticleField(root_widget, count=64)
        self.particles.lower()

        layout = QHBoxLayout(root_widget)
        layout.setContentsMargins(13, 13, 13, 13)
        layout.setSpacing(13)

        self.stack = QStackedWidget()
        self.mission = MissionControlPage(
            engine, event_bus, event_store
        )
        self.dashboard = DashboardPage(engine, operator)
        self.scan = ScanPage(engine)
        self.network = NetworkPage(engine)
        self.terminal = TerminalPage(engine, self.navigate_to_label)
        self.cases = CasesPage(engine)
        self.events = EventFeedPage(event_bus, event_store)
        self.history = HistoryPage(engine)
        self.reports = ReportsPage(engine)
        self.assistant = AssistantPage(engine)
        self.plugins = PluginsPage(engine)
        self.settings = SettingsPage(engine)
        self.platform = PlatformPage(self.navigate_to_label)

        self.pages = [
            ("MISSION CONTROL", self.mission),
            ("PLATFORM", self.platform),
            ("DASHBOARD", self.dashboard),
            ("LIVE SCAN", self.scan),
            ("NETWORK MAP", self.network),
            ("TERMINAL", self.terminal),
            ("CASES", self.cases),
            ("EVENT FEED", self.events),
            ("HISTORY", self.history),
            ("REPORTS", self.reports),
            ("AI ASSISTANT", self.assistant),
            ("PLUGINS", self.plugins),
            ("SETTINGS", self.settings),
        ]
        self.page_index = {label: index for index, (label, _) in enumerate(self.pages)}

        for _, page in self.pages:
            self.stack.addWidget(page)

        self.dock = Dock(self.pages, self.show_page)
        layout.addWidget(self.dock)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(10)
        content_layout.addWidget(self.stack, 1)
        self.command_bar = CommandBar(self.execute_command)
        content_layout.addWidget(self.command_bar)
        layout.addWidget(content, 1)

        self.toast = Toast(root_widget)
        if self.event_bus:
            self.event_bus.subscribe(self.toast.show_event)
            from ..events import EventLevel
            self.event_bus.emit(
                "platform",
                f"Operator {operator} entered the BLACKTERM workspace.",
                title="Platform Ready",
                level=EventLevel.SUCCESS,
                module="platform",
            )

        self.scan.scan_started.connect(self.network.scan_started)
        self.scan.scan_port_observed.connect(self.network.scan_progress)
        self.scan.scan_completed.connect(self.network.scan_finished)
        self.settings.theme_changed.connect(self.apply_theme)
        self.apply_theme(engine.config.theme)
        root_widget.installEventFilter(self)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.particles.setGeometry(self.centralWidget().rect())
        if getattr(self, "toast", None) and self.toast.isVisible():
            rect = self.centralWidget().rect()
            self.toast.move(rect.right() - self.toast.width() - 24, rect.bottom() - self.toast.height() - 24)

    def eventFilter(self, watched, event):
        if event.type() == QEvent.MouseMove:
            self.particles.set_mouse_position(event.position())
        return super().eventFilter(watched, event)

    def execute_command(self, command):
        parts = command.strip().lower().split()
        if not parts:
            return
        if parts[0] == "open" and len(parts) > 1:
            mapping = {
                "mission": "MISSION CONTROL",
                "control": "MISSION CONTROL",
                "platform": "PLATFORM",
                "dashboard": "DASHBOARD",
                "scan": "LIVE SCAN",
                "map": "NETWORK MAP",
                "terminal": "TERMINAL",
                "cases": "CASES",
                "events": "EVENT FEED",
                "feed": "EVENT FEED",
                "history": "HISTORY",
                "reports": "REPORTS",
                "assistant": "AI ASSISTANT",
                "plugins": "PLUGINS",
                "settings": "SETTINGS",
            }
            label = mapping.get(parts[1])
            if label:
                self.navigate_to_label(label)
                return
        if parts[0] == "history":
            self.navigate_to_label("HISTORY")
        elif parts[0] == "scan":
            self.navigate_to_label("LIVE SCAN")
        elif parts[0] == "cases":
            self.navigate_to_label("CASES")
        elif parts[0] == "report":
            self.navigate_to_label("REPORTS")
        else:
            self.navigate_to_label("TERMINAL")

    def navigate_to_label(self, label):
        index = self.page_index.get(label)
        if index is not None:
            self.dock.buttons[label].setChecked(True)
            self.show_page(index)

    def show_page(self, index):
        self.stack.setCurrentIndex(index)
        page = self.pages[index][1]
        if hasattr(page, "refresh"):
            page.refresh()

        animation = QPropertyAnimation(page, b"windowOpacity", self)
        animation.setDuration(220)
        animation.setStartValue(0.68)
        animation.setEndValue(1.0)
        animation.setEasingCurve(QEasingCurve.OutCubic)
        animation.start()
        self._page_animation = animation

    def apply_theme(self, name):
        self.setStyleSheet(stylesheet(name))
