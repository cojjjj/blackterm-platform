from __future__ import annotations

from html import escape

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ...attack_surface import AttackSurface, SurfaceFinding, build_attack_surface
from ..attack_surface_graph import AttackSurfaceGraph, GraphNodeData
from .attack_surface import FindingDialog, CVSS_BY_SEVERITY, RISK_COLORS


class InvestigationWorkspacePage(QWidget):
    """Dedicated analyst workspace where the graph is the primary interface."""

    backRequested = Signal()

    def __init__(self, engine):
        super().__init__()
        self.engine = engine
        self.current_surface: AttackSurface | None = None
        self._selected_finding: SurfaceFinding | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("Investigation Workspace")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Explore the complete attack surface, pivot between nodes, and inspect evidence.")
        subtitle.setObjectName("muted")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header.addLayout(title_box)
        header.addStretch(1)

        self.scan_selector = QComboBox()
        self.scan_selector.setMinimumWidth(330)
        self.scan_selector.currentIndexChanged.connect(self.load_selected)
        header.addWidget(self.scan_selector)

        refresh = QPushButton("REFRESH")
        refresh.clicked.connect(self.refresh)
        fit = QPushButton("FIT GRAPH")
        fit.setObjectName("primary")
        fit.clicked.connect(self._fit_graph)
        replay = QPushButton("REPLAY")
        replay.clicked.connect(self._replay_graph)
        back = QPushButton("BACK TO SURFACE")
        back.clicked.connect(self.backRequested.emit)
        header.addWidget(refresh)
        header.addWidget(fit)
        header.addWidget(replay)
        header.addWidget(back)
        root.addLayout(header)

        status_row = QHBoxLayout()
        self.target_label = QLabel("TARGET: —")
        self.risk_label = QLabel("RISK: —")
        self.operation_label = QLabel("OPERATION: —")
        self.graph_status = QLabel("Awaiting telemetry")
        self.graph_status.setObjectName("muted")
        for label in (self.target_label, self.risk_label, self.operation_label):
            label.setStyleSheet(
                "background:#07111f;border:1px solid #244667;border-radius:8px;"
                "padding:7px 10px;font-weight:800;color:#bcd8f4;"
            )
            status_row.addWidget(label)
        status_row.addStretch(1)
        status_row.addWidget(self.graph_status)
        root.addLayout(status_row)

        splitter = QSplitter(Qt.Vertical)
        splitter.setChildrenCollapsible(False)

        graph_panel = QFrame()
        graph_panel.setObjectName("panel")
        graph_layout = QVBoxLayout(graph_panel)
        graph_layout.setContentsMargins(8, 8, 8, 8)
        hint = QLabel(
            "Hover to trace relationships • Click to inspect • Double-click to collapse • "
            "Ctrl+wheel to zoom • Drag to pan"
        )
        hint.setObjectName("muted")
        graph_layout.addWidget(hint)
        self.graph = AttackSurfaceGraph()
        self.graph.setMinimumHeight(500)
        self.graph.nodeActivated.connect(self.inspect_node)
        rendered = getattr(self.graph, "graphRendered", None)
        if rendered is not None:
            rendered.connect(self._graph_rendered)
        graph_layout.addWidget(self.graph, 1)
        splitter.addWidget(graph_panel)

        details = QFrame()
        details.setObjectName("panel")
        details_layout = QHBoxLayout(details)
        details_layout.setContentsMargins(12, 10, 12, 10)

        identity = QVBoxLayout()
        self.node_kind = QLabel("NODE DETAILS")
        self.node_kind.setObjectName("muted")
        self.node_title = QLabel("Select a node")
        self.node_title.setWordWrap(True)
        self.node_title.setStyleSheet("font-size:20px;font-weight:900;color:#f5f7ff;")
        identity.addWidget(self.node_kind)
        identity.addWidget(self.node_title)
        identity.addStretch(1)
        details_layout.addLayout(identity, 2)

        self.node_body = QTextEdit()
        self.node_body.setReadOnly(True)
        self.node_body.setFrameShape(QFrame.NoFrame)
        self.node_body.setStyleSheet(
            "QTextEdit{background:#07111f;border:1px solid #244667;border-radius:9px;"
            "padding:9px;color:#bcd8f4;}"
        )
        self.node_body.setPlainText("Select a target, service, technology, or finding node to inspect it.")
        details_layout.addWidget(self.node_body, 5)

        actions = QVBoxLayout()
        self.dossier_button = QPushButton("OPEN FINDING DOSSIER")
        self.dossier_button.setObjectName("primary")
        self.dossier_button.setEnabled(False)
        self.dossier_button.clicked.connect(self.open_dossier)
        center = QPushButton("CENTER / FIT")
        center.clicked.connect(self._fit_graph)
        actions.addWidget(self.dossier_button)
        actions.addWidget(center)
        actions.addStretch(1)
        details_layout.addLayout(actions, 2)
        splitter.addWidget(details)
        splitter.setSizes([650, 190])
        root.addWidget(splitter, 1)

        self.refresh()

    def refresh(self):
        selected = self.scan_selector.currentData()
        rows = self.engine.repository.list_recent(100)
        self.scan_selector.blockSignals(True)
        self.scan_selector.clear()
        for row in rows:
            label = f"#{row['id']}  {row['target']}  •  {row['open_ports']} open  •  {row['finished_at'][:19]}"
            self.scan_selector.addItem(label, row["id"])
        self.scan_selector.blockSignals(False)
        if selected is not None:
            index = self.scan_selector.findData(selected)
            if index >= 0:
                self.scan_selector.setCurrentIndex(index)
        self.load_selected()

    def select_scan(self, scan_id):
        self.refresh()
        if scan_id is None:
            return
        index = self.scan_selector.findData(scan_id)
        if index >= 0:
            self.scan_selector.setCurrentIndex(index)
            self.load_selected()

    def load_selected(self):
        scan_id = self.scan_selector.currentData()
        if scan_id is None:
            self.render_surface(None)
            return
        result = self.engine.repository.get(int(scan_id))
        self.render_surface(build_attack_surface(result) if result else None)

    def render_surface(self, surface: AttackSurface | None):
        self.current_surface = surface
        self._selected_finding = None
        self.dossier_button.setEnabled(False)
        self.graph.render_surface(surface)
        if surface is None:
            self.target_label.setText("TARGET: —")
            self.risk_label.setText("RISK: —")
            self.operation_label.setText("OPERATION: —")
            self.graph_status.setText("Awaiting telemetry")
            self.node_kind.setText("NODE DETAILS")
            self.node_title.setText("Select a node")
            self.node_body.setPlainText("Run or select a completed scan to populate the workspace.")
            return

        color = RISK_COLORS.get(surface.risk_level, "#31b7ff")
        self.target_label.setText(f"TARGET: {surface.target}")
        self.risk_label.setText(f"RISK: {surface.risk_level} ({surface.risk_score}/100)")
        self.risk_label.setStyleSheet(
            f"background:{color}18;border:1px solid {color};border-radius:8px;"
            f"padding:7px 10px;font-weight:900;color:{color};"
        )
        self.operation_label.setText(f"OPERATION: {surface.operation_id or 'SAVED SCAN'}")
        self.graph_status.setText(
            f"{len(surface.open_ports)} ports • {len(surface.technologies)} technologies • "
            f"{len(surface.findings)} findings"
        )
        self.inspect_node(GraphNodeData("target", surface.target, surface.hostname or surface.ip))

    def _fit_graph(self):
        fit = getattr(self.graph, "fit_graph", None)
        if callable(fit):
            fit()
        elif self.graph.scene() and not self.graph.scene().sceneRect().isEmpty():
            self.graph.fitInView(self.graph.scene().sceneRect(), Qt.KeepAspectRatio)

    def _replay_graph(self):
        replay = getattr(self.graph, "replay", None)
        if callable(replay):
            replay()
        elif self.current_surface is not None:
            self.graph.render_surface(self.current_surface)

    def _graph_rendered(self, nodes: int, relationships: int):
        self.graph_status.setText(f"{nodes} nodes • {relationships} relationships")

    def inspect_node(self, node: GraphNodeData):
        self._selected_finding = None
        self.dossier_button.setEnabled(False)
        self.node_kind.setText(node.kind.upper())
        self.node_title.setText(node.title)

        surface = self.current_surface
        if surface is None:
            self.node_body.setPlainText(node.subtitle)
            return

        if node.kind == "target":
            body = (
                f"IP: {surface.ip}\nHostname: {surface.hostname or 'Unknown'}\n"
                f"Profile: {surface.profile.upper()}\nRisk: {surface.risk_level} ({surface.risk_score}/100)\n"
                f"Surface health: {surface.attack_surface_score}/100\nOpen ports: "
                f"{', '.join(map(str, surface.open_ports)) or 'None'}"
            )
        elif node.kind == "service":
            related = [f for f in surface.findings if self._matches(f, node.port, node.service)]
            body = (
                f"Port: TCP/{node.port}\nService: {node.service or node.subtitle}\n"
                f"Related findings: {len(related)}\n\n"
                + ("\n".join(f"• {f.severity.upper()}: {f.title}" for f in related) or "No related findings.")
            )
            if related:
                self._selected_finding = related[0]
                self.dossier_button.setEnabled(True)
        elif node.kind == "technology":
            body = f"Technology: {node.technology or node.title}\nDetected from available scan evidence."
        elif node.kind == "finding" and node.finding_index is not None and node.finding_index < len(surface.findings):
            finding = surface.findings[node.finding_index]
            self._selected_finding = finding
            self.dossier_button.setEnabled(True)
            body = (
                f"Severity: {finding.severity.upper()}\n"
                f"CVSS context: {CVSS_BY_SEVERITY.get(finding.severity, '—')}\n\n"
                f"{finding.detail}\n\nEvidence: {finding.evidence or 'No evidence recorded.'}\n\n"
                f"Recommendation: {finding.recommendation or 'Review the observed exposure.'}"
            )
        else:
            body = node.subtitle
        self.node_body.setPlainText(body)

    @staticmethod
    def _matches(finding: SurfaceFinding, port: int | None, service: str | None) -> bool:
        if port is None:
            return False
        evidence = (finding.evidence or "").lower()
        title = (finding.title or "").lower()
        return f"{port}/tcp" in evidence or f"tcp/{port}" in evidence or bool(service and service.lower() in title)

    def open_dossier(self):
        if self._selected_finding is not None:
            FindingDialog(self._selected_finding, self).exec()
