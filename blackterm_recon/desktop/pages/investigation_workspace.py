from __future__ import annotations

from html import escape

from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QProgressBar,
    QPushButton,
    QSplitter,
    QTabWidget,
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

        intelligence_strip = QGridLayout()
        intelligence_strip.setHorizontalSpacing(8)

        risk_panel = QFrame()
        risk_panel.setObjectName("panel")
        risk_layout = QVBoxLayout(risk_panel)
        risk_layout.setContentsMargins(10, 8, 10, 8)
        risk_layout.addWidget(QLabel("OPERATIONAL RISK"))
        self.risk_score_value = QLabel("—")
        self.risk_score_value.setStyleSheet("font-size:28px;font-weight:900;color:#31b7ff;")
        self.risk_score_bar = QProgressBar()
        self.risk_score_bar.setRange(0, 100)
        self.risk_score_bar.setValue(0)
        self.risk_score_bar.setFormat("RISK %p%")
        risk_layout.addWidget(self.risk_score_value)
        risk_layout.addWidget(self.risk_score_bar)
        intelligence_strip.addWidget(risk_panel, 0, 0)

        exposure_panel = QFrame()
        exposure_panel.setObjectName("panel")
        exposure_layout = QVBoxLayout(exposure_panel)
        exposure_layout.setContentsMargins(10, 8, 10, 8)
        exposure_layout.addWidget(QLabel("EXPOSURE SUMMARY"))
        self.exposure_summary = QLabel("No scan selected")
        self.exposure_summary.setObjectName("muted")
        self.exposure_summary.setWordWrap(True)
        exposure_layout.addWidget(self.exposure_summary)
        intelligence_strip.addWidget(exposure_panel, 0, 1)

        ai_panel = QFrame()
        ai_panel.setObjectName("panel")
        ai_layout = QVBoxLayout(ai_panel)
        ai_layout.setContentsMargins(10, 8, 10, 8)
        ai_layout.addWidget(QLabel("BLACKTERM AI // NEXT ACTION"))
        self.ai_recommendation = QLabel("Select an investigation to generate analyst guidance.")
        self.ai_recommendation.setObjectName("muted")
        self.ai_recommendation.setWordWrap(True)
        ai_layout.addWidget(self.ai_recommendation)
        intelligence_strip.addWidget(ai_panel, 0, 2)
        intelligence_strip.setColumnStretch(0, 1)
        intelligence_strip.setColumnStretch(1, 2)
        intelligence_strip.setColumnStretch(2, 3)
        root.addLayout(intelligence_strip)

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
        graph_body = QSplitter(Qt.Horizontal)
        graph_body.setChildrenCollapsible(False)
        self.graph = AttackSurfaceGraph()
        self.graph.setMinimumHeight(500)
        self.graph.nodeActivated.connect(self.inspect_node)
        rendered = getattr(self.graph, "graphRendered", None)
        if rendered is not None:
            rendered.connect(self._graph_rendered)
        graph_body.addWidget(self.graph)

        self.analyst_tabs = QTabWidget()
        self.analyst_tabs.setMinimumWidth(310)
        self.analyst_tabs.setMaximumWidth(420)

        evidence_tab = QWidget()
        evidence_layout = QVBoxLayout(evidence_tab)
        self.evidence_title = QLabel("NO NODE SELECTED")
        self.evidence_title.setStyleSheet("font-size:16px;font-weight:900;color:#31b7ff;")
        self.evidence_body = QTextEdit()
        self.evidence_body.setReadOnly(True)
        self.evidence_body.setPlainText("Select a graph node to inspect collected evidence and relationships.")
        evidence_layout.addWidget(self.evidence_title)
        evidence_layout.addWidget(self.evidence_body, 1)
        self.analyst_tabs.addTab(evidence_tab, "EVIDENCE")

        timeline_tab = QWidget()
        timeline_layout = QVBoxLayout(timeline_tab)
        self.timeline_status = QLabel("INVESTIGATION TIMELINE")
        self.timeline_status.setObjectName("muted")
        self.timeline_list = QListWidget()
        timeline_layout.addWidget(self.timeline_status)
        timeline_layout.addWidget(self.timeline_list, 1)
        self.analyst_tabs.addTab(timeline_tab, "TIMELINE")

        ai_tab = QWidget()
        ai_tab_layout = QVBoxLayout(ai_tab)
        self.ai_confidence = QLabel("CONFIDENCE // —")
        self.ai_confidence.setStyleSheet("font-weight:900;color:#36e6b0;")
        self.ai_brief = QTextEdit()
        self.ai_brief.setReadOnly(True)
        self.ai_brief.setPlainText("BLACKTERM AI is waiting for investigation context.")
        ai_tab_layout.addWidget(self.ai_confidence)
        ai_tab_layout.addWidget(self.ai_brief, 1)
        self.analyst_tabs.addTab(ai_tab, "AI ANALYST")

        graph_body.addWidget(self.analyst_tabs)
        graph_body.setSizes([980, 330])
        graph_layout.addWidget(graph_body, 1)
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

        self._replay_steps: list[str] = []
        self._replay_index = 0
        self._replay_timer = QTimer(self)
        self._replay_timer.setInterval(420)
        self._replay_timer.timeout.connect(self._advance_replay)
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
            self.risk_score_value.setText("—")
            self.risk_score_bar.setValue(0)
            self.exposure_summary.setText("No scan selected")
            self.ai_recommendation.setText("Select an investigation to generate analyst guidance.")
            self.timeline_list.clear()
            self.evidence_title.setText("NO NODE SELECTED")
            self.evidence_body.setPlainText("Select a graph node to inspect collected evidence and relationships.")
            self.ai_confidence.setText("CONFIDENCE // —")
            self.ai_brief.setPlainText("BLACKTERM AI is waiting for investigation context.")
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
        self.risk_score_value.setText(f"{surface.risk_level}  {surface.risk_score}/100")
        self.risk_score_value.setStyleSheet(
            f"font-size:24px;font-weight:900;color:{color};"
        )
        self.risk_score_bar.setValue(surface.risk_score)
        finding_counts = {}
        for finding in surface.findings:
            severity = (finding.severity or "info").upper()
            finding_counts[severity] = finding_counts.get(severity, 0) + 1
        severity_text = " • ".join(
            f"{name}: {count}" for name, count in sorted(finding_counts.items())
        ) or "No findings"
        self.exposure_summary.setText(
            f"{len(surface.open_ports)} exposed service(s) • "
            f"{len(surface.technologies)} technology signal(s)\n{severity_text}"
        )
        recommendation = self._build_ai_recommendation(surface)
        self.ai_recommendation.setText(recommendation)
        self._populate_timeline(surface)
        confidence = min(98, 62 + len(surface.open_ports) * 4 + len(surface.findings) * 5 + len(surface.technologies) * 3)
        self.ai_confidence.setText(f"CONFIDENCE // {confidence}%")
        self.ai_brief.setPlainText(self._build_ai_brief(surface, recommendation, confidence))
        self.inspect_node(GraphNodeData("target", surface.target, surface.hostname or surface.ip))

    def _fit_graph(self):
        fit = getattr(self.graph, "fit_graph", None)
        if callable(fit):
            fit()
        elif self.graph.scene() and not self.graph.scene().sceneRect().isEmpty():
            self.graph.fitInView(self.graph.scene().sceneRect(), Qt.KeepAspectRatio)

    def _replay_graph(self):
        if self.current_surface is None:
            return
        replay = getattr(self.graph, "replay", None)
        if callable(replay):
            replay()
        self.analyst_tabs.setCurrentIndex(1)
        self.timeline_list.clear()
        self._replay_steps = self._timeline_entries(self.current_surface)
        self._replay_index = 0
        self.timeline_status.setText("REPLAY ACTIVE // reconstructing investigation")
        self._replay_timer.start()

    def _advance_replay(self):
        if self._replay_index >= len(self._replay_steps):
            self._replay_timer.stop()
            self.timeline_status.setText("REPLAY COMPLETE // evidence chain reconstructed")
            return
        self.timeline_list.addItem(self._replay_steps[self._replay_index])
        self.timeline_list.scrollToBottom()
        self._replay_index += 1

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
        self.evidence_title.setText(f"{node.kind.upper()} // {node.title}")
        self.evidence_body.setPlainText(body)
        self.analyst_tabs.setCurrentIndex(0)

    @staticmethod
    def _timeline_entries(surface: AttackSurface) -> list[str]:
        entries = [
            f"01  SCOPE LOCKED      {surface.target}",
            f"02  ASSET RESOLVED    {surface.hostname or surface.ip}",
            f"03  PROFILE APPLIED   {surface.profile.upper()}",
            f"04  PORT DISCOVERY    {len(surface.open_ports)} exposed service(s)",
        ]
        for port, service in list(zip(surface.open_ports, surface.services))[:8]:
            entries.append(f"{len(entries)+1:02d}  SERVICE OBSERVED  TCP/{port} {service}")
        if surface.technologies:
            entries.append(f"{len(entries)+1:02d}  TECH CORRELATED    {', '.join(surface.technologies[:4])}")
        entries.append(f"{len(entries)+1:02d}  RISK CALCULATED    {surface.risk_level} {surface.risk_score}/100")
        entries.append(f"{len(entries)+1:02d}  AI BRIEF READY     analyst context generated")
        return entries

    def _populate_timeline(self, surface: AttackSurface) -> None:
        self.timeline_list.clear()
        for entry in self._timeline_entries(surface):
            self.timeline_list.addItem(entry)
        self.timeline_status.setText(f"{self.timeline_list.count()} EVENTS // evidence chain complete")

    @staticmethod
    def _build_ai_brief(surface: AttackSurface, recommendation: str, confidence: int) -> str:
        services = ", ".join(f"TCP/{p}" for p in surface.open_ports[:8]) or "No exposed TCP services"
        tech = ", ".join(surface.technologies[:6]) or "No technology fingerprints"
        return (
            "INVESTIGATION SUMMARY\n\n"
            f"Target: {surface.target}\n"
            f"Risk: {surface.risk_level} ({surface.risk_score}/100)\n"
            f"Confidence: {confidence}%\n"
            f"Observed services: {services}\n"
            f"Technology context: {tech}\n\n"
            "ANALYST ASSESSMENT\n"
            f"{recommendation}\n\n"
            "SAFE NEXT STEPS\n"
            "• Validate ownership and authorized scope\n"
            "• Preserve scan evidence and timestamps\n"
            "• Review the highest-severity dossier\n"
            "• Compare against historical scans before escalation"
        )

    @staticmethod
    def _build_ai_recommendation(surface: AttackSurface) -> str:
        ports = set(surface.open_ports)
        if any(port in ports for port in (3389, 5900, 22)):
            return (
                "Remote administration exposure detected. Validate authorization, restrict source ranges, "
                "review authentication controls, and correlate the service with known asset ownership."
            )
        if any(port in ports for port in (445, 139)):
            return (
                "File-sharing services are externally visible. Confirm segmentation, inspect SMB hardening, "
                "and review the related finding dossier before expanding enumeration."
            )
        if any(port in ports for port in (80, 443, 8080, 8443)):
            return (
                "Web exposure is present. Capture application evidence, inventory technologies, review TLS, "
                "and run authorized content discovery against the confirmed scope."
            )
        if surface.findings:
            highest = max(
                surface.findings,
                key=lambda item: {"critical": 4, "high": 3, "medium": 2, "low": 1}.get(
                    (item.severity or "").lower(), 0
                ),
            )
            return (
                f"Prioritize {highest.severity.upper()} finding: {highest.title}. "
                "Open the dossier, verify the evidence, and document remediation ownership."
            )
        return (
            "No immediate high-confidence exposure was identified. Preserve the evidence, validate asset "
            "ownership, and compare this scan with historical results for meaningful changes."
        )

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
