from __future__ import annotations

from PySide6.QtCore import QEvent
from PySide6.QtWidgets import QHBoxLayout, QMainWindow, QStackedWidget, QVBoxLayout, QWidget

from .command_bar import CommandBar
from .dock import Dock
from .event_feed import EventFeedPage, Toast
from .pages.assistant import AssistantPage
from .pages.cases import CasesPage
from .pages.dashboard import DashboardPage
from .pages.history import HistoryPage
from .pages.mission_control import MissionControlPage
from .operator_dashboard_page import OperatorDashboardPage
from .pages.network import NetworkPage
from .pages.osint import OSINTPage
from .pages.threat_intelligence import ThreatIntelligencePage
from .pages.platform import PlatformPage
from .pages.plugins import PluginsPage
from .pages.reports import ReportsPage
from .pages.scan import ScanPage
from .pages.attack_surface import AttackSurfacePage
from .pages.investigation_workspace import InvestigationWorkspacePage
from .pages.settings import SettingsPage
from .pages.terminal import TerminalPage
from .theme import stylesheet
from .autonomous import AutonomousInvestigation
from .event_bridge import QtEventBridge
from .living_interface import BootOverlay, FadeController
from .render_engine import RenderSurface
from .premium_style import premium_stylesheet


class MainWindow(QMainWindow):
    def __init__(self, engine, operator="OPERATOR", event_bus=None, event_store=None):
        super().__init__()
        self.engine = engine
        self.operator = operator
        self.event_bus = event_bus
        self.event_store = event_store
        self.setWindowTitle("BLACKTERM RECON v5.7 // Interactive Attack Surface Graph")
        self.resize(1540, 920)
        self.setMinimumSize(1160, 740)
        self.setMouseTracking(True)

        root_widget = QWidget()
        root_widget.setObjectName("rootWindow")
        self.setCentralWidget(root_widget)
        self.render_surface = RenderSurface(root_widget, particle_count=42)
        self.render_surface.lower()

        layout = QHBoxLayout(root_widget)
        layout.setContentsMargins(13, 13, 13, 13)
        layout.setSpacing(13)

        self.fade_controller = FadeController(self)
        self.stack = QStackedWidget()
        self.mission = MissionControlPage(
            engine, event_bus, event_store
        )
        self.operator_dashboard = OperatorDashboardPage(
            engine, event_bus, operator=operator
        )
        self.dashboard = DashboardPage(engine, operator)
        self.scan = ScanPage(engine)
        self.attack_surface = AttackSurfacePage(engine)
        self.investigation_workspace = InvestigationWorkspacePage(engine)
        self.autonomous = AutonomousInvestigation(engine, event_bus, self)
        self.network = NetworkPage(engine)
        self.osint = OSINTPage(engine, event_bus)
        self.threat_intelligence = ThreatIntelligencePage(engine, event_bus)
        self.terminal = TerminalPage(engine, self.navigate_to_label)
        self.cases = CasesPage(engine, event_bus)
        self.events = EventFeedPage(event_bus, event_store)
        self.history = HistoryPage(engine)
        self.reports = ReportsPage(engine)
        self.assistant = AssistantPage(engine)
        self.plugins = PluginsPage(engine)
        self.settings = SettingsPage(engine)
        self.platform = PlatformPage(self.navigate_to_label)

        self.pages = [
            ("MISSION CONTROL", self.mission),
            ("OPERATOR DASHBOARD", self.operator_dashboard),
            ("PLATFORM", self.platform),
            ("DASHBOARD", self.dashboard),
            ("LIVE SCAN", self.scan),
            ("ATTACK SURFACE", self.attack_surface),
            ("INVESTIGATION WORKSPACE", self.investigation_workspace),
            ("NETWORK MAP", self.network),
            ("OSINT", self.osint),
            ("THREAT INTELLIGENCE", self.threat_intelligence),
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

        self.scan.scan_completed.connect(self.attack_surface.show_result)
        self.attack_surface.investigationRequested.connect(self.open_investigation_workspace)
        self.investigation_workspace.backRequested.connect(
            lambda: self.navigate_to_label("ATTACK SURFACE")
        )

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
        self.event_bridge = QtEventBridge(self.event_bus, self) if self.event_bus else None
        if self.event_bridge:
            self.event_bridge.connect(self.toast.show_event)
            from ..events import EventLevel
            self.event_bus.emit(
                "platform",
                f"Operator {operator} entered the BLACKTERM workspace.",
                title="Platform Ready",
                level=EventLevel.SUCCESS,
                module="platform",
            )

        self.scan.scan_started.connect(self.network.scan_started)
        self.scan.scan_started.connect(self.autonomous.scan_started)
        self.scan.scan_port_observed.connect(self.network.scan_progress)
        self.scan.scan_port_observed.connect(self.autonomous.port_observed)
        self.scan.scan_completed.connect(self.network.scan_finished)
        self.scan.scan_completed.connect(self.autonomous.scan_completed)
        self.scan.scan_completed.connect(lambda scan_id, result: self.cases.refresh())
        self.autonomous.case_created.connect(self.cases.refresh)
        self.autonomous.case_created.connect(self.cases.select_case)
        self.autonomous.case_created.connect(self.open_case)
        self.osint.case_created.connect(self.cases.refresh)
        self.osint.case_created.connect(self.open_case)
        self.threat_intelligence.case_created.connect(self.cases.refresh)
        self.threat_intelligence.case_created.connect(self.open_case)
        self.operator_dashboard.open_case_requested.connect(self.open_case)
        self.operator_dashboard.live_investigation_requested.connect(
            self.open_live_investigation
        )
        self.operator_dashboard.mission_control_requested.connect(
            lambda: self.navigate_to_label("MISSION CONTROL")
        )
        self.settings.theme_changed.connect(self.apply_theme)
        self.apply_theme(engine.config.theme)
        root_widget.installEventFilter(self)


    def open_investigation_workspace(self, scan_id=None):
        self.navigate_to_label("INVESTIGATION WORKSPACE")
        self.investigation_workspace.select_scan(scan_id)

    def open_live_investigation(self):
        self.navigate_to_label("CASES")
        if hasattr(self.cases, "open_intelligence_engine"):
            self.cases.open_intelligence_engine()

    def open_case(self, case_id: int):
        self.navigate_to_label("CASES")
        self.cases.refresh()
        self.cases.select_case(case_id)
        self.cases.load_case()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        rect = self.centralWidget().rect()
        self.render_surface.setGeometry(rect)
        if hasattr(self, "boot_overlay"):
            self.boot_overlay.setGeometry(rect.adjusted(18, 18, -18, -18))
        if getattr(self, "toast", None) and self.toast.isVisible():
            self.toast.move(
                rect.right() - self.toast.width() - 24,
                rect.bottom() - self.toast.height() - 24,
            )

    def closeEvent(self, event):
        if getattr(self, "render_surface", None):
            self.render_surface.shutdown()
        if getattr(self, "event_bridge", None):
            self.event_bridge.close()
        super().closeEvent(event)

    def eventFilter(self, watched, event):
        # RenderSurface currently does not expose mouse-reactive particles.
        # Keep this guarded so mouse movement can never crash the main window.
        if event.type() == QEvent.MouseMove:
            render_surface = getattr(self, "render_surface", None)
            set_mouse_position = getattr(render_surface, "set_mouse_position", None)
            if callable(set_mouse_position):
                set_mouse_position(event.position())
        return super().eventFilter(watched, event)

    def execute_command(self, command):
        parts = command.strip().lower().split()
        if not parts:
            return
        if parts[0] == "open" and len(parts) > 1:
            mapping = {
                "mission": "MISSION CONTROL",
                "control": "MISSION CONTROL",
                "operator": "OPERATOR DASHBOARD",
                "home": "OPERATOR DASHBOARD",
                "platform": "PLATFORM",
                "dashboard": "DASHBOARD",
                "scan": "LIVE SCAN",
                "attack": "ATTACK SURFACE",
                "surface": "ATTACK SURFACE",
                "investigation": "INVESTIGATION WORKSPACE",
                "workspace": "INVESTIGATION WORKSPACE",
                "graph": "INVESTIGATION WORKSPACE",
                "map": "NETWORK MAP",
                "osint": "OSINT",
                "threat": "THREAT INTELLIGENCE",
                "intel": "THREAT INTELLIGENCE",
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
        if parts[0] in {"operator", "home"}:
            self.navigate_to_label("OPERATOR DASHBOARD")
        elif parts[0] == "osint":
            self.navigate_to_label("OSINT")
        elif parts[0] == "history":
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
            self.dock.select_label(label)
            self.show_page(index)

    def show_page(self, index):
        self.stack.setCurrentIndex(index)
        page = self.pages[index][1]
        if hasattr(page, "refresh"):
            page.refresh()
        self.fade_controller.fade_in(page, 210)

    def apply_theme(self, name):
        self.setStyleSheet(stylesheet(name) + premium_stylesheet())
