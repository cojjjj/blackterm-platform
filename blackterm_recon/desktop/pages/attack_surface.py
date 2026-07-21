from __future__ import annotations

from html import escape

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ...attack_surface import AttackSurface, SurfaceFinding, build_attack_surface
from ..attack_surface_graph import AttackSurfaceGraph, GraphNodeData


RISK_COLORS = {
    "LOW": "#36e6b0",
    "MEDIUM": "#f5c451",
    "HIGH": "#ff8a4c",
    "CRITICAL": "#ff5577",
    "INFO": "#31b7ff",
}

CVSS_BY_SEVERITY = {
    "critical": "9.5",
    "high": "8.0",
    "medium": "5.5",
    "low": "2.5",
    "info": "0.0",
}

CATEGORY_LABELS = {
    "network": "NETWORK",
    "web": "WEB",
    "remote_admin": "REMOTE",
    "databases": "DATABASE",
}


class FindingDialog(QDialog):
    def __init__(self, finding: SurfaceFinding, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle(f"BLACKTERM RECON // {finding.title}")
        self.setMinimumSize(720, 480)
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(12)

        color = RISK_COLORS.get(finding.severity.upper(), "#31b7ff")
        badge = QLabel(f"  {finding.severity.upper()}  •  CVSS {CVSS_BY_SEVERITY.get(finding.severity, '—')}  ")
        badge.setStyleSheet(
            f"background:{color}22;color:{color};border:1px solid {color};"
            "border-radius:10px;font-weight:900;padding:6px 10px;"
        )
        badge.setMaximumWidth(210)
        root.addWidget(badge)

        title = QLabel(finding.title)
        title.setStyleSheet("font-size:22px;font-weight:900;color:#f5f7ff;")
        title.setWordWrap(True)
        root.addWidget(title)

        content = QLabel(
            "<b>ANALYST CONTEXT</b><br>"
            f"{escape(finding.detail)}<br><br>"
            "<b>EVIDENCE</b><br>"
            f"{escape(finding.evidence or 'No additional evidence recorded.')}<br><br>"
            "<b>RECOMMENDATION</b><br>"
            f"{escape(finding.recommendation or 'Review and validate the observed exposure.')}<br><br>"
            "<b>MITRE ATT&CK CONTEXT</b><br>"
            f"{escape(self._mitre_context(finding))}<br><br>"
            "<b>VALIDATION NOTE</b><br>"
            "This finding is based on observed service exposure. Confirm configuration, authentication, "
            "patch level, and intended network scope before assigning final risk."
        )
        content.setWordWrap(True)
        content.setTextFormat(Qt.RichText)
        content.setTextInteractionFlags(Qt.TextSelectableByMouse)
        content.setStyleSheet("font-size:13px;line-height:1.45;color:#c8d7eb;")

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        holder = QWidget()
        holder_layout = QVBoxLayout(holder)
        holder_layout.addWidget(content)
        holder_layout.addStretch(1)
        scroll.setWidget(holder)
        root.addWidget(scroll, 1)

        close = QPushButton("CLOSE DOSSIER")
        close.setObjectName("primary")
        close.clicked.connect(self.accept)
        root.addWidget(close, 0, Qt.AlignRight)

    @staticmethod
    def _mitre_context(finding: SurfaceFinding) -> str:
        title = finding.title.lower()
        if "remote" in title or "rdp" in title or "ssh" in title:
            return "T1021 — Remote Services"
        if "smb" in title or "microsoft-ds" in title or "netbios" in title:
            return "T1021.002 — SMB/Windows Admin Shares"
        if "database" in title:
            return "T1190 — Exploit Public-Facing Application (contextual review)"
        if "web" in title:
            return "T1190 — Exploit Public-Facing Application (contextual review)"
        return "No direct technique assigned; treat as exposure intelligence."


class AttackSurfacePage(QWidget):
    investigationRequested = Signal(object)

    def __init__(self, engine):
        super().__init__()
        self.engine = engine
        self.current_surface: AttackSurface | None = None
        self._category_values: dict[str, QLabel] = {}
        self._category_bars: dict[str, QProgressBar] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 8, 10, 10)
        root.setSpacing(10)

        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("Attack Surface Intelligence")
        title.setObjectName("pageTitle")
        subtitle = QLabel(
            "Consolidated exposure, service context, technologies, and prioritized analyst findings."
        )
        subtitle.setObjectName("muted")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header.addLayout(title_box)
        header.addStretch(1)
        self.scan_selector = QComboBox()
        self.scan_selector.setMinimumWidth(300)
        self.scan_selector.currentIndexChanged.connect(self.load_selected)
        workspace = QPushButton("OPEN INVESTIGATION WORKSPACE")
        workspace.setObjectName("primary")
        workspace.clicked.connect(self._open_investigation_workspace)
        refresh = QPushButton("REFRESH")
        refresh.setObjectName("primary")
        refresh.clicked.connect(self.refresh)
        header.addWidget(self.scan_selector)
        header.addWidget(workspace)
        header.addWidget(refresh)
        root.addLayout(header)

        metrics = QGridLayout()
        metrics.setHorizontalSpacing(10)
        self.target_value = self._metric(metrics, 0, "TARGET", "No completed scan")
        self.operation_value = self._metric(metrics, 1, "OPERATION", "—")
        self.risk_value = self._metric(metrics, 2, "OVERALL RISK", "—")
        self.score_value = self._metric(metrics, 3, "SURFACE SCORE", "—")
        self.port_value = self._metric(metrics, 4, "OPEN PORTS", "0")
        root.addLayout(metrics)

        score_panel = QFrame()
        score_panel.setObjectName("panel")
        score_layout = QVBoxLayout(score_panel)
        score_header = QHBoxLayout()
        score_header.addWidget(QLabel("ATTACK SURFACE HEALTH"))
        score_header.addStretch(1)
        self.score_caption = QLabel("Awaiting completed scan")
        self.score_caption.setObjectName("muted")
        score_header.addWidget(self.score_caption)
        score_layout.addLayout(score_header)
        self.score_bar = QProgressBar()
        self.score_bar.setRange(0, 100)
        self.score_bar.setValue(0)
        self.score_bar.setFormat("%v / 100")
        score_layout.addWidget(self.score_bar)
        root.addWidget(score_panel)

        categories = QGridLayout()
        categories.setHorizontalSpacing(10)
        for column, key in enumerate(("network", "web", "remote_admin", "databases")):
            card = QFrame()
            card.setObjectName("panel")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(12, 9, 12, 9)
            label = QLabel(CATEGORY_LABELS[key])
            label.setObjectName("muted")
            value = QLabel("0")
            value.setStyleSheet("font-size:20px;font-weight:900;color:#31b7ff;")
            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setTextVisible(False)
            bar.setFixedHeight(7)
            card_layout.addWidget(label)
            card_layout.addWidget(value)
            card_layout.addWidget(bar)
            categories.addWidget(card, 0, column)
            self._category_values[key] = value
            self._category_bars[key] = bar
        root.addLayout(categories)

        graph_panel = QFrame()
        graph_panel.setObjectName("panel")
        graph_layout = QVBoxLayout(graph_panel)
        graph_layout.setContentsMargins(10, 10, 10, 10)
        graph_layout.setSpacing(8)

        graph_header = QHBoxLayout()
        graph_header.addWidget(QLabel("INTERACTIVE RECON WORKSPACE"))
        graph_header.addStretch(1)
        self.graph_status = QLabel("Awaiting telemetry")
        self.graph_status.setObjectName("muted")
        graph_header.addWidget(self.graph_status)
        fit_button = QPushButton("FIT")
        fit_button.clicked.connect(self._fit_graph)
        replay_button = QPushButton("REPLAY")
        replay_button.clicked.connect(self._replay_graph)
        self.detail_toggle = QPushButton("HIDE DETAILS")
        self.detail_toggle.clicked.connect(self._toggle_graph_details)
        graph_header.addWidget(fit_button)
        graph_header.addWidget(replay_button)
        graph_header.addWidget(self.detail_toggle)
        graph_layout.addLayout(graph_header)

        graph_hint = QLabel(
            "Hover to trace relationships • Click to inspect • Double-click to collapse • Ctrl+wheel to zoom • Drag to pan"
        )
        graph_hint.setObjectName("muted")
        graph_layout.addWidget(graph_hint)

        graph_body = QHBoxLayout()
        graph_body.setSpacing(10)
        self.surface_graph = AttackSurfaceGraph()
        self.surface_graph.nodeActivated.connect(self.open_graph_node)
        self.surface_graph.graphRendered.connect(self._graph_rendered)
        graph_body.addWidget(self.surface_graph, 7)

        self.graph_detail = QFrame()
        self.graph_detail.setObjectName("panel")
        self.graph_detail.setMinimumWidth(270)
        self.graph_detail.setMaximumWidth(360)
        detail_layout = QVBoxLayout(self.graph_detail)
        detail_layout.setContentsMargins(12, 12, 12, 12)
        self.graph_detail_kind = QLabel("NODE DETAILS")
        self.graph_detail_kind.setObjectName("muted")
        self.graph_detail_title = QLabel("Select a node")
        self.graph_detail_title.setWordWrap(True)
        self.graph_detail_title.setStyleSheet("font-size:18px;font-weight:900;color:#f5f7ff;")
        self.graph_detail_body = QTextEdit()
        self.graph_detail_body.setReadOnly(True)
        self.graph_detail_body.setFrameShape(QFrame.NoFrame)
        self.graph_detail_body.setStyleSheet(
            "QTextEdit{background:#07111f;border:1px solid #244667;border-radius:9px;"
            "padding:8px;color:#bcd8f4;}"
        )
        self.graph_dossier_button = QPushButton("OPEN FINDING DOSSIER")
        self.graph_dossier_button.setObjectName("primary")
        self.graph_dossier_button.setEnabled(False)
        self.graph_dossier_button.clicked.connect(self.open_graph_finding_dossier)
        detail_layout.addWidget(self.graph_detail_kind)
        detail_layout.addWidget(self.graph_detail_title)
        detail_layout.addWidget(self.graph_detail_body, 1)
        detail_layout.addWidget(self.graph_dossier_button)
        graph_body.addWidget(self.graph_detail, 2)
        graph_layout.addLayout(graph_body, 1)
        root.addWidget(graph_panel, 3)
        self._graph_selected_finding: SurfaceFinding | None = None

        body = QHBoxLayout()
        body.setSpacing(10)

        left = QFrame()
        left.setObjectName("panel")
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(QLabel("EXPOSURE PROFILE"))
        self.network_text = QLabel("Run an authorized scan to build a surface profile.")
        self.network_text.setWordWrap(True)
        self.network_text.setTextInteractionFlags(Qt.TextSelectableByMouse)
        left_layout.addWidget(self.network_text)

        left_layout.addSpacing(6)
        left_layout.addWidget(QLabel("DETECTED TECHNOLOGIES"))
        self.technology_box = QWidget()
        self.technology_layout = QVBoxLayout(self.technology_box)
        self.technology_layout.setContentsMargins(0, 0, 0, 0)
        self.technology_layout.setSpacing(6)
        left_layout.addWidget(self.technology_box)

        left_layout.addSpacing(8)
        left_layout.addWidget(QLabel("AI ANALYST"))
        self.ai_summary = QLabel("Awaiting attack-surface telemetry.")
        self.ai_summary.setWordWrap(True)
        self.ai_summary.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.ai_summary.setStyleSheet(
            "background:#07111f;border:1px solid #244667;border-radius:9px;"
            "padding:10px;color:#bcd8f4;"
        )
        left_layout.addWidget(self.ai_summary)
        left_layout.addStretch(1)
        body.addWidget(left, 2)

        right = QFrame()
        right.setObjectName("panel")
        right_layout = QVBoxLayout(right)
        findings_header = QHBoxLayout()
        findings_header.addWidget(QLabel("PRIORITIZED FINDINGS"))
        findings_header.addStretch(1)
        self.finding_counts = QLabel("0 findings")
        self.finding_counts.setObjectName("muted")
        findings_header.addWidget(self.finding_counts)
        right_layout.addLayout(findings_header)

        hint = QLabel("Double-click a finding to open its evidence dossier.")
        hint.setObjectName("muted")
        right_layout.addWidget(hint)

        self.findings = QTableWidget(0, 5)
        self.findings.setHorizontalHeaderLabels(
            ["SEVERITY", "CVSS", "FINDING", "EVIDENCE", "RECOMMENDATION"]
        )
        self.findings.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.findings.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.findings.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.findings.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.findings.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.findings.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.findings.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.findings.setWordWrap(True)
        self.findings.doubleClicked.connect(self.open_selected_finding)
        right_layout.addWidget(self.findings)
        body.addWidget(right, 5)
        root.addLayout(body, 1)

        self.refresh()


    def _open_investigation_workspace(self):
        """Open the dedicated full-screen graph for the selected scan."""
        self.investigationRequested.emit(self.scan_selector.currentData())

    def _metric(self, grid: QGridLayout, column: int, title: str, value: str) -> QLabel:
        card = QFrame()
        card.setObjectName("panel")
        layout = QVBoxLayout(card)
        label = QLabel(title)
        label.setObjectName("muted")
        number = QLabel(value)
        number.setStyleSheet("font-size:22px;font-weight:900;color:#31b7ff;")
        number.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(label)
        layout.addWidget(number)
        grid.addWidget(card, 0, column)
        return number

    def refresh(self):
        selected_id = self.scan_selector.currentData()
        rows = self.engine.repository.list_recent(100)
        self.scan_selector.blockSignals(True)
        self.scan_selector.clear()
        for row in rows:
            label = f"#{row['id']}  {row['target']}  •  {row['open_ports']} open  •  {row['finished_at'][:19]}"
            self.scan_selector.addItem(label, row["id"])
        self.scan_selector.blockSignals(False)
        if selected_id is not None:
            index = self.scan_selector.findData(selected_id)
            if index >= 0:
                self.scan_selector.setCurrentIndex(index)
        self.load_selected()

    def show_result(self, scan_id: int, result):
        index = self.scan_selector.findData(scan_id)
        if index < 0:
            self.refresh()
            index = self.scan_selector.findData(scan_id)
        if index >= 0:
            self.scan_selector.setCurrentIndex(index)
        self.render_surface(build_attack_surface(result))

    def load_selected(self):
        scan_id = self.scan_selector.currentData()
        if scan_id is None:
            self.render_surface(None)
            return
        result = self.engine.repository.get(int(scan_id))
        self.render_surface(build_attack_surface(result) if result else None)

    def _clear_technologies(self):
        while self.technology_layout.count():
            item = self.technology_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _render_technologies(self, technologies: list[str]):
        self._clear_technologies()
        if not technologies:
            empty = QLabel("No technology signatures detected yet")
            empty.setObjectName("muted")
            empty.setWordWrap(True)
            self.technology_layout.addWidget(empty)
            return

        row: QHBoxLayout | None = None
        for index, technology in enumerate(technologies):
            if index % 2 == 0:
                row = QHBoxLayout()
                row.setSpacing(6)
                self.technology_layout.addLayout(row)
            chip = QLabel(technology)
            chip.setAlignment(Qt.AlignCenter)
            chip.setStyleSheet(
                "background:#10243a;border:1px solid #2d6a94;border-radius:9px;"
                "padding:6px 9px;color:#7ed7ff;font-weight:800;"
            )
            assert row is not None
            row.addWidget(chip)
        if row is not None:
            row.addStretch(1)

    @staticmethod
    def _analyst_summary(surface: AttackSurface) -> str:
        counts = surface.severity_counts
        lines = [
            f"Assessment complete for {surface.target}.",
            f"{len(surface.open_ports)} open TCP port(s) and {len(surface.services)} classified service(s) were observed.",
        ]
        if surface.technologies:
            lines.append(f"Technology context: {', '.join(surface.technologies[:5])}.")
        if counts["critical"] or counts["high"]:
            lines.append(
                f"Priority: {counts['critical']} critical and {counts['high']} high-severity finding(s) require review."
            )
        elif counts["medium"]:
            lines.append(f"Priority: review {counts['medium']} medium-severity finding(s).")
        else:
            lines.append("No high-priority exposure was identified in this scan range.")

        if surface.findings:
            recommendation = next(
                (item.recommendation for item in surface.findings if item.severity != "info"),
                surface.findings[0].recommendation,
            )
            if recommendation:
                lines.append(f"Recommendation: {recommendation}")
        return "\n\n".join(lines)

    def render_surface(self, surface: AttackSurface | None):
        self.current_surface = surface
        self.findings.setRowCount(0)
        if surface is None:
            self.target_value.setText("No completed scan")
            self.operation_value.setText("—")
            self.risk_value.setText("—")
            self.risk_value.setStyleSheet("font-size:22px;font-weight:900;color:#31b7ff;")
            self.score_value.setText("—")
            self.port_value.setText("0")
            self.score_bar.setValue(0)
            self.score_caption.setText("Awaiting completed scan")
            self.network_text.setText("Run an authorized scan to build a surface profile.")
            self._render_technologies([])
            self.ai_summary.setText("Awaiting attack-surface telemetry.")
            self.finding_counts.setText("0 findings")
            self.surface_graph.render_surface(None)
            self.graph_status.setText("Awaiting telemetry")
            self.graph_detail_kind.setText("NODE DETAILS")
            self.graph_detail_title.setText("Select a node")
            self.graph_detail_body.setPlainText("Click a target, service, technology, or finding node to inspect it here.")
            self.graph_dossier_button.setEnabled(False)
            self._graph_selected_finding = None
            for key in self._category_values:
                self._category_values[key].setText("0")
                self._category_bars[key].setValue(0)
            return

        color = RISK_COLORS.get(surface.risk_level, "#31b7ff")
        self.target_value.setText(surface.target)
        self.operation_value.setText(surface.operation_id or "SAVED SCAN")
        self.risk_value.setText(f"● {surface.risk_level}")
        self.risk_value.setStyleSheet(
            f"font-size:20px;font-weight:900;color:{color};background:{color}18;"
            f"border:1px solid {color};border-radius:10px;padding:5px 8px;"
        )
        self.score_value.setText(f"{surface.attack_surface_score}/100")
        self.port_value.setText(str(len(surface.open_ports)))
        self.score_bar.setValue(surface.attack_surface_score)
        self.score_caption.setText(
            f"Risk {surface.risk_score}/100 • {len(surface.services)} classified service(s)"
        )

        ports = ", ".join(str(port) for port in surface.open_ports) or "None observed"
        services = ", ".join(surface.services) or "No classified services"
        self.network_text.setText(
            f"IP: {surface.ip}\n"
            f"Hostname: {surface.hostname or 'Unknown'}\n"
            f"Profile: {surface.profile.upper()}\n\n"
            f"Open ports: {ports}\n"
            f"Services: {services}"
        )
        self._render_technologies(surface.technologies)
        self.surface_graph.render_surface(surface)
        self.graph_detail_kind.setText("TARGET")
        self.graph_detail_title.setText(surface.target)
        self.graph_detail_body.setPlainText(
            f"Risk: {surface.risk_level} ({surface.risk_score}/100)\n"
            f"Open ports: {len(surface.open_ports)}\n"
            f"Technologies: {len(surface.technologies)}\n"
            f"Findings: {len(surface.findings)}\n\n"
            "Select any graph node for deeper context."
        )
        self.graph_dossier_button.setEnabled(False)
        self._graph_selected_finding = None
        self.ai_summary.setText(self._analyst_summary(surface))

        categories = surface.exposure_categories
        maximum = max(1, max(categories.values(), default=1))
        for key, value_label in self._category_values.items():
            value = int(categories.get(key, 0))
            value_label.setText(str(value))
            self._category_bars[key].setValue(round((value / maximum) * 100) if value else 0)

        counts = surface.severity_counts
        self.finding_counts.setText(
            f"{len(surface.findings)} findings • "
            f"{counts['critical']} critical • {counts['high']} high • {counts['medium']} medium"
        )
        for finding in surface.findings:
            row = self.findings.rowCount()
            self.findings.insertRow(row)
            values = [
                finding.severity.upper(),
                CVSS_BY_SEVERITY.get(finding.severity, "—"),
                f"{finding.title}\n{finding.detail}",
                finding.evidence or "—",
                finding.recommendation or "—",
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setToolTip(value)
                item.setData(Qt.UserRole, row)
                if column == 0:
                    item.setForeground(QColor(RISK_COLORS.get(finding.severity.upper(), "#b7c7db")))
                elif column == 1:
                    item.setTextAlignment(Qt.AlignCenter)
                self.findings.setItem(row, column, item)
            self.findings.resizeRowToContents(row)

    def _fit_graph(self):
        self.surface_graph.fit_graph()

    def _replay_graph(self):
        self.surface_graph.replay()

    def _toggle_graph_details(self):
        visible = self.graph_detail.isVisible()
        self.graph_detail.setVisible(not visible)
        self.detail_toggle.setText("SHOW DETAILS" if visible else "HIDE DETAILS")
        self.surface_graph.fit_graph()

    def _graph_rendered(self, node_count: int, edge_count: int):
        self.graph_status.setText(f"{node_count} nodes • {edge_count} relationships")

    def open_graph_node(self, node: GraphNodeData):
        if self.current_surface is None:
            return

        self._graph_selected_finding = None
        self.graph_dossier_button.setEnabled(False)
        self.graph_detail_kind.setText(node.kind.replace("_", " ").upper())
        self.graph_detail_title.setText(node.title)

        if node.kind == "finding" and node.finding_index is not None:
            if 0 <= node.finding_index < len(self.current_surface.findings):
                finding = self.current_surface.findings[node.finding_index]
                self._graph_selected_finding = finding
                self.graph_dossier_button.setEnabled(True)
                self.graph_detail_body.setPlainText(
                    f"Severity: {finding.severity.upper()}\n"
                    f"CVSS context: {CVSS_BY_SEVERITY.get(finding.severity, '—')}\n\n"
                    f"{finding.detail}\n\n"
                    f"Evidence\n{finding.evidence or 'No evidence recorded'}\n\n"
                    f"Recommendation\n{finding.recommendation or 'No recommendation recorded'}"
                )
                return

        if node.kind == "service" and node.port is not None:
            matching = next(
                (
                    finding
                    for finding in self.current_surface.findings
                    if f"{node.port}/tcp" in (finding.evidence or "")
                    or f"tcp/{node.port}" in (finding.evidence or "").lower()
                    or (node.service and node.service.lower() in finding.title.lower())
                ),
                None,
            )
            if matching is not None:
                self._graph_selected_finding = matching
                self.graph_dossier_button.setEnabled(True)

        self.graph_detail_body.setPlainText(self._graph_node_details(node))

    def open_graph_finding_dossier(self):
        if self._graph_selected_finding is not None:
            FindingDialog(self._graph_selected_finding, self).exec()

    def _graph_node_details(self, node: GraphNodeData) -> str:
        assert self.current_surface is not None
        surface = self.current_surface
        if node.kind == "internet":
            return (
                f"Assessment profile: {surface.profile.upper()}\n"
                f"Operation: {surface.operation_id or 'SAVED SCAN'}\n"
                "This node represents the authorized assessment scope, not proof of public internet exposure."
            )
        if node.kind == "target":
            return (
                f"Target: {surface.target}\n"
                f"IP: {surface.ip}\n"
                f"Hostname: {surface.hostname or 'Unknown'}\n"
                f"Overall risk: {surface.risk_level} ({surface.risk_score}/100)\n"
                f"Open TCP ports: {len(surface.open_ports)}"
            )
        if node.kind == "service":
            mapped = "A related finding is available. Use OPEN FINDING DOSSIER for full evidence." if self._graph_selected_finding else "No dedicated finding dossier was mapped to this node."
            return (
                f"Port: TCP/{node.port}\n"
                f"Service classification: {node.service or 'Unknown'}\n\n"
                f"{mapped}\n\n"
                "Validate the service banner, authentication controls, patch level, and intended network scope."
            )
        if node.kind == "technology":
            return (
                f"Technology: {node.technology or node.title}\n\n"
                "This signature was inferred from scan telemetry. Confirm the exact product and version "
                "before using it for vulnerability correlation."
            )
        if node.kind == "finding":
            return node.subtitle
        return node.subtitle

    def open_selected_finding(self):
        if self.current_surface is None:
            return
        row = self.findings.currentRow()
        if row < 0 or row >= len(self.current_surface.findings):
            return
        FindingDialog(self.current_surface.findings[row], self).exec()
