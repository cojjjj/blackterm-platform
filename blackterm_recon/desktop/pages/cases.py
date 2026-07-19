from __future__ import annotations
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox, QDialog, QDialogButtonBox, QFormLayout,
    QFileDialog, QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QMessageBox, QPushButton, QSlider, QSplitter, QTabWidget, QTabBar, QTableWidget,
    QTableWidgetItem, QTextEdit, QTreeWidget, QTreeWidgetItem, QVBoxLayout,
    QWidget,
)
from ...case_reporting import write_case_report
from ...investigation_engine import assess_case
from ...correlation_engine import correlate_case
from ..investigation_graph import InvestigationGraph
from ..intelligence_page import IntelligencePage
from ..operator_dashboard_page import OperatorDashboardPage


class NewCaseDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create Investigation")
        form = QFormLayout(self)
        self.name = QLineEdit()
        self.description = QTextEdit()
        self.description.setMaximumHeight(100)
        form.addRow("Case name", self.name)
        form.addRow("Scope / description", self.description)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)


class CasesPage(QWidget):
    def __init__(self, engine, event_bus=None):
        super().__init__()
        self.engine = engine
        self.event_bus = event_bus
        self.timeline_events = []
        self.correlation_report = None

        root = QVBoxLayout(self)
        head = QHBoxLayout()
        title = QLabel("Investigation Workspace")
        title.setObjectName("pageTitle")
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search cases, notes, and evidence...")
        self.search.textChanged.connect(self.refresh)
        operator_button = QPushButton("OPERATOR DASHBOARD")
        operator_button.clicked.connect(self.open_operator_dashboard)
        intelligence_button = QPushButton("LIVE INVESTIGATION")
        intelligence_button.clicked.connect(self.open_intelligence_engine)
        new = QPushButton("NEW CASE")
        new.setObjectName("primary")
        new.clicked.connect(self.create_case)
        head.addWidget(title)
        head.addStretch()
        head.addWidget(self.search, 1)
        head.addWidget(operator_button)
        head.addWidget(intelligence_button)
        head.addWidget(new)
        root.addLayout(head)

        split = QSplitter(Qt.Horizontal)
        root.addWidget(split, 1)
        left = QFrame()
        left.setObjectName("panel")
        left_layout = QVBoxLayout(left)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["ID", "CASE", "STATUS", "SCANS", "CREATED"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setColumnWidth(0, 48)
        self.table.setColumnWidth(1, 185)
        self.table.setColumnWidth(2, 92)
        self.table.setColumnWidth(3, 66)
        self.table.itemSelectionChanged.connect(self.load_case)
        left_layout.addWidget(self.table)
        self.scan_choice = QComboBox()
        attach = QPushButton("ATTACH SCAN")
        attach.clicked.connect(self.attach_scan)
        row = QHBoxLayout()
        row.addWidget(self.scan_choice, 1)
        row.addWidget(attach)
        left_layout.addLayout(row)
        split.addWidget(left)

        right = QFrame()
        right.setObjectName("panel")
        right_layout = QVBoxLayout(right)
        self.case_title = QLabel("SELECT A CASE")
        self.case_title.setObjectName("sectionTitle")
        right_layout.addWidget(self.case_title)
        status_row = QHBoxLayout()
        self.status = QComboBox()
        self.status.addItems(["OPEN", "ACTIVE", "REVIEW", "CLOSED"])
        self.status.currentTextChanged.connect(self.change_status)
        self.ai = QPushButton("RUN AI ANALYSIS")
        self.ai.clicked.connect(self.run_ai)
        self.correlate_button = QPushButton("CORRELATE INTELLIGENCE")
        self.correlate_button.setObjectName("primary")
        self.correlate_button.clicked.connect(self.run_correlation)
        status_row.addWidget(QLabel("STATUS"))
        status_row.addWidget(self.status)
        status_row.addStretch()
        status_row.addWidget(self.correlate_button)
        status_row.addWidget(self.ai)
        right_layout.addLayout(status_row)

        self.tabs = QTabWidget()
        right_layout.addWidget(self.tabs, 1)
        self.overview = QTextEdit()
        self.overview.setReadOnly(True)
        self.tabs.addTab(self.overview, "OVERVIEW")

        notes = QWidget()
        notes_layout = QVBoxLayout(notes)
        self.notes_list = QTextEdit()
        self.notes_list.setReadOnly(True)
        self.note = QTextEdit()
        self.note.setMaximumHeight(100)
        self.note.setPlaceholderText("Record observations, next steps, or evidence context...")
        save = QPushButton("SAVE NOTE")
        save.clicked.connect(self.add_note)
        notes_layout.addWidget(self.notes_list, 1)
        notes_layout.addWidget(self.note)
        notes_layout.addWidget(save)
        self.tabs.addTab(notes, "NOTES")

        evidence_tab = QWidget()
        evidence_layout = QVBoxLayout(evidence_tab)
        self.evidence = QTableWidget(0, 5)
        self.evidence.setHorizontalHeaderLabels(["TYPE", "TITLE", "SOURCE", "SHA-256", "CREATED"])
        evidence_layout.addWidget(self.evidence, 1)
        evidence_row = QHBoxLayout()
        add_text = QPushButton("ADD TEXT")
        add_text.clicked.connect(self.add_text_evidence)
        add_file = QPushButton("ADD FILE")
        add_file.clicked.connect(self.add_file_evidence)
        capture = QPushButton("CAPTURE WORKSPACE")
        capture.clicked.connect(self.capture_workspace)
        evidence_row.addWidget(add_text)
        evidence_row.addWidget(add_file)
        evidence_row.addWidget(capture)
        evidence_row.addStretch()
        evidence_layout.addLayout(evidence_row)
        self.tabs.addTab(evidence_tab, "EVIDENCE LOCKER")

        timeline_tab = QWidget()
        timeline_layout = QVBoxLayout(timeline_tab)
        self.timeline = QListWidget()
        self.replay = QSlider(Qt.Horizontal)
        self.replay.valueChanged.connect(self.replay_timeline)
        self.replay_label = QLabel("Timeline replay ready")
        timeline_layout.addWidget(self.timeline, 1)
        timeline_layout.addWidget(self.replay_label)
        timeline_layout.addWidget(self.replay)
        self.tabs.addTab(timeline_tab, "TIMELINE")

        correlation_tab = QWidget()
        correlation_layout = QVBoxLayout(correlation_tab)
        metrics = QHBoxLayout()
        self.correlation_priority = QLabel("PRIORITY // --")
        self.correlation_score = QLabel("SCORE // --")
        self.correlation_confidence = QLabel("CONFIDENCE // --")
        for widget in (self.correlation_priority, self.correlation_score, self.correlation_confidence):
            widget.setObjectName("sectionTitle")
            metrics.addWidget(widget)
        metrics.addStretch()
        correlation_layout.addLayout(metrics)
        correlation_split = QSplitter(Qt.Horizontal)
        self.correlation_text = QTextEdit()
        self.correlation_text.setReadOnly(True)
        self.correlation_text.setPlaceholderText("Run intelligence correlation to connect scans, targets, services, and evidence.")
        self.relationships = QTreeWidget()
        self.relationships.setHeaderLabels(["INTELLIGENCE RELATIONSHIP", "DETAIL"])
        self.relationships.setAlternatingRowColors(True)
        correlation_split.addWidget(self.correlation_text)
        correlation_split.addWidget(self.relationships)
        correlation_split.setSizes([580, 520])
        correlation_layout.addWidget(correlation_split, 1)
        self.tabs.addTab(correlation_tab, "CORRELATION")

        graph_tab = QWidget()
        graph_layout = QVBoxLayout(graph_tab)
        self.investigation_graph = InvestigationGraph()
        graph_layout.addWidget(self.investigation_graph)
        self.tabs.addTab(graph_tab, "GRAPH")

        analyst = QWidget()
        analyst_layout = QVBoxLayout(analyst)
        self.analysis = QTextEdit()
        self.analysis.setReadOnly(True)
        analyst_layout.addWidget(self.analysis)
        self.tabs.addTab(analyst, "AI INVESTIGATION")

        export_tab = QWidget()
        export_layout = QVBoxLayout(export_tab)
        export_layout.addWidget(QLabel("Export the complete case package with scope, scans, notes, evidence hashes, and timeline."))
        formats = QHBoxLayout()
        for label, fmt, ext in [("HTML", "html", ".html"), ("PDF", "pdf", ".pdf"), ("MARKDOWN", "md", ".md"), ("JSON", "json", ".json")]:
            button = QPushButton(label)
            button.clicked.connect(lambda checked=False, f=fmt, e=ext: self.export_case(f, e))
            formats.addWidget(button)
        formats.addStretch()
        export_layout.addLayout(formats)
        export_layout.addStretch()
        self.tabs.addTab(export_tab, "EXPORT")

        self.operator_dashboard = OperatorDashboardPage(
            self.engine, self.event_bus, operator="TYLER"
        )
        self.operator_dashboard.open_case_requested.connect(self.open_generated_case)
        self.operator_dashboard.live_investigation_requested.connect(
            self.open_intelligence_engine
        )
        self.operator_dashboard.mission_control_requested.connect(
            self.open_mission_control
        )
        self.tabs.addTab(self.operator_dashboard, "OPERATOR DASHBOARD")

        self.intelligence_page = IntelligencePage(self.engine, self.event_bus)
        self.intelligence_page.case_created.connect(self.open_generated_case)
        self.tabs.addTab(self.intelligence_page, "LIVE INTELLIGENCE")

        split.addWidget(right)
        split.setSizes([520, 900])
        self.refresh()

    def open_operator_dashboard(self):
        self.operator_dashboard.refresh()
        self.tabs.setCurrentWidget(self.operator_dashboard)

    def open_mission_control(self):
        window = self.window()
        # Support BLACKTERM's existing page-opening conventions without hard coupling.
        for method_name in ("open_page", "navigate", "show_page"):
            method = getattr(window, method_name, None)
            if callable(method):
                for key in ("mission", "mission_control", "dashboard"):
                    try:
                        method(key)
                        return
                    except Exception:
                        continue
        QMessageBox.information(
            self,
            "Mission Control",
            "Use the Mission Control icon in the BLACKTERM dock.",
        )

    def open_intelligence_engine(self):
        self.tabs.setCurrentWidget(self.intelligence_page)
        self.intelligence_page.target.setFocus()

    def open_generated_case(self, case_id):
        self.refresh()
        if hasattr(self, "operator_dashboard"):
            self.operator_dashboard.refresh()
        self.select_case(case_id)
        self.tabs.setCurrentIndex(0)

    def selected_case_id(self):
        rows = self.table.selectionModel().selectedRows() if self.table.selectionModel() else []
        return int(self.table.item(rows[0].row(), 0).text()) if rows else None

    def refresh(self):
        query = self.search.text().strip() if hasattr(self, "search") else ""
        cases = self.engine.repository.search_cases(query) if query else self.engine.repository.list_cases()
        self.table.setRowCount(len(cases))
        for row, case in enumerate(cases):
            values = [case["id"], case["name"], case["status"], case["scan_count"], case["created_at"][:19]]
            for column, value in enumerate(values):
                self.table.setItem(row, column, QTableWidgetItem(str(value)))
        current = self.scan_choice.currentData() if hasattr(self, "scan_choice") else None
        self.scan_choice.clear()
        for scan in self.engine.repository.list_recent(150):
            self.scan_choice.addItem(f"#{scan['id']} {scan['target']} - {scan['open_ports']} open", scan["id"])
        if current:
            index = self.scan_choice.findData(current)
            self.scan_choice.setCurrentIndex(max(0, index))
        if self.table.rowCount() and self.selected_case_id() is None:
            self.table.selectRow(0)

    def create_case(self):
        dialog = NewCaseDialog(self)
        if dialog.exec() and dialog.name.text().strip():
            case_id = self.engine.repository.create_case(dialog.name.text(), dialog.description.toPlainText())
            self.refresh()
            self.select_case(case_id)

    def select_case(self, case_id):
        for row in range(self.table.rowCount()):
            if int(self.table.item(row, 0).text()) == case_id:
                self.table.selectRow(row)
                break

    def load_case(self):
        case_id = self.selected_case_id()
        if case_id is None:
            return
        case = next(case for case in self.engine.repository.list_cases() if case["id"] == case_id)
        self.case_title.setText(f"CASE #{case_id} // {case['name']}")
        self.status.blockSignals(True)
        self.status.setCurrentText(case["status"])
        self.status.blockSignals(False)
        scans = self.engine.repository.case_scans(case_id)
        notes = self.engine.repository.case_notes(case_id)
        evidence = self.engine.repository.case_evidence(case_id)
        self.timeline_events = self.engine.repository.case_timeline(case_id)
        if scans:
            scan_text = "\n".join(
                f"#{scan['id']} {scan['target']} ({scan['ip']}) - {scan['open_ports']} open ports"
                for scan in scans
            )
            self.overview.setPlainText(f"SCOPE\n{case['description'] or 'No scope recorded.'}\n\nATTACHED SCANS\n{scan_text}")
        else:
            self.overview.setPlainText(f"SCOPE\n{case['description'] or 'No scope recorded.'}\n\nNo scans attached.")
        self.notes_list.setPlainText("\n\n".join(f"[{note['created_at'][:19]}]\n{note['note']}" for note in notes) or "No notes recorded.")
        self.evidence.setRowCount(len(evidence))
        for row, item in enumerate(evidence):
            sha = str(item.get("sha256", ""))
            values = [item["evidence_type"], item["title"], item.get("source") or item.get("file_path"), (sha[:18] + "...") if sha else "", item["created_at"][:19]]
            for column, value in enumerate(values):
                self.evidence.setItem(row, column, QTableWidgetItem(str(value)))
        self.timeline.clear()
        for item in self.timeline_events:
            self.timeline.addItem(f"{item['created_at'][11:19]}  {item['event_type']:<9}  {item['title']}")
        self.replay.setMaximum(max(0, len(self.timeline_events) - 1))
        self.replay.setValue(self.replay.maximum())
        self.clear_correlation()

    def clear_correlation(self):
        self.correlation_report = None
        self.relationships.clear()
        self.correlation_text.clear()
        self.correlation_priority.setText("PRIORITY // --")
        self.correlation_score.setText("SCORE // --")
        self.correlation_confidence.setText("CONFIDENCE // --")
        if hasattr(self, "investigation_graph"):
            self.investigation_graph.clear_graph()

    def run_correlation(self):
        case_id = self.selected_case_id()
        if not case_id:
            return
        self.correlate_button.setEnabled(False)
        self.correlate_button.setText("CORRELATING...")
        try:
            report = correlate_case(self.engine.repository, case_id)
            self.correlation_report = report
            self.correlation_text.setPlainText(report.to_text())
            self.correlation_priority.setText(f"PRIORITY // {report.level}")
            self.correlation_score.setText(f"SCORE // {report.score}/100")
            self.correlation_confidence.setText(f"CONFIDENCE // {report.confidence}%")
            self.render_relationships(report)
            self.investigation_graph.set_report(report)
            self.engine.repository.add_case_evidence(
                case_id,
                "AI",
                "Intelligence correlation report",
                "BLACKTERM Correlation Engine",
                report.to_text(),
            )
            self.engine.repository.add_case_timeline(
                case_id,
                "INTEL",
                "Intelligence correlation completed",
                f"{report.level} priority / {report.confidence}% confidence / {len(report.edges)} relationships",
            )
            if self.event_bus:
                from ...events import EventLevel
                self.event_bus.emit(
                    "case",
                    report.summary,
                    title="Intelligence Correlation Complete",
                    level=EventLevel.AI,
                    module="correlation",
                    metadata={
                        "case_id": case_id,
                        "score": report.score,
                        "priority": report.level,
                        "confidence": report.confidence,
                        "relationships": len(report.edges),
                    },
                )
            self.tabs.setCurrentIndex(4)
        except Exception as exc:
            QMessageBox.critical(self, "Correlation failed", str(exc))
        finally:
            self.correlate_button.setEnabled(True)
            self.correlate_button.setText("CORRELATE INTELLIGENCE")

    def render_relationships(self, report):
        self.relationships.clear()
        node_lookup = {node.node_id: node for node in report.nodes}
        groups = {}
        for edge in report.edges:
            source = node_lookup.get(edge.source)
            target = node_lookup.get(edge.target)
            if not source or not target:
                continue
            group = groups.get(source.node_id)
            if group is None:
                group = QTreeWidgetItem([f"{source.kind} // {source.label}", source.detail])
                group.setExpanded(True)
                groups[source.node_id] = group
                self.relationships.addTopLevelItem(group)
            child = QTreeWidgetItem([
                f"{edge.relationship.upper()} -> {target.kind} // {target.label}",
                f"{target.detail} | confidence {edge.confidence}%".strip(" |"),
            ])
            if target.risk >= 18:
                child.setForeground(0, QBrush(QColor("#ff6b8a")))
            elif target.risk >= 10:
                child.setForeground(0, QBrush(QColor("#f4c46b")))
            group.addChild(child)
        self.relationships.resizeColumnToContents(0)

    def change_status(self, status):
        case_id = self.selected_case_id()
        if case_id:
            self.engine.repository.update_case_status(case_id, status)
            self.refresh()
            self.select_case(case_id)

    def attach_scan(self):
        case_id = self.selected_case_id()
        scan_id = self.scan_choice.currentData()
        if case_id and scan_id:
            self.engine.repository.attach_scan_to_case(case_id, int(scan_id))
            self.load_case()

    def add_note(self):
        case_id = self.selected_case_id()
        text = self.note.toPlainText().strip()
        if case_id and text:
            self.engine.repository.add_case_note(case_id, text)
            self.note.clear()
            self.load_case()

    def add_text_evidence(self):
        case_id = self.selected_case_id()
        if not case_id:
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Add Text Evidence")
        form = QFormLayout(dialog)
        kind = QComboBox()
        kind.addItems(["OBSERVATION", "WHOIS", "DNS", "HEADERS", "SSL", "AI", "LOG", "OTHER"])
        title = QLineEdit()
        source = QLineEdit()
        content = QTextEdit()
        form.addRow("Type", kind)
        form.addRow("Title", title)
        form.addRow("Source", source)
        form.addRow("Content", content)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        form.addRow(buttons)
        if dialog.exec() and title.text().strip():
            self.engine.repository.add_case_evidence(case_id, kind.currentText(), title.text(), source.text(), content.toPlainText())
            self.load_case()

    def add_file_evidence(self):
        case_id = self.selected_case_id()
        path, _ = QFileDialog.getOpenFileName(self, "Add Evidence File")
        if case_id and path:
            self.engine.repository.add_case_evidence(case_id, "FILE", Path(path).name, path, "", path)
            self.load_case()

    def capture_workspace(self):
        case_id = self.selected_case_id()
        if not case_id:
            return
        folder = Path.home() / ".blackterm-recon" / "evidence" / f"case_{case_id}"
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / "workspace.png"
        self.window().grab().save(str(path), "PNG")
        self.engine.repository.add_case_evidence(case_id, "SCREENSHOT", "BLACKTERM workspace capture", "desktop", "", str(path))
        self.load_case()

    def run_ai(self):
        case_id = self.selected_case_id()
        if not case_id:
            return
        self.ai.setEnabled(False)
        self.ai.setText("ANALYZING...")
        try:
            assessment = assess_case(self.engine.repository, case_id)
            text = assessment.to_text()
            self.analysis.setPlainText(text)
            self.engine.repository.add_case_evidence(case_id, "AI", "AI investigation summary", "BLACKTERM AI", text)
            self.engine.repository.add_case_timeline(case_id, "AI", "AI investigation completed", f"{assessment.level} risk / {assessment.confidence}% confidence")
            if self.event_bus:
                from ...events import EventLevel
                self.event_bus.emit(
                    "case",
                    f"Case #{case_id}: {assessment.summary}",
                    title="AI Case Analysis Complete",
                    level=EventLevel.AI,
                    module="cases",
                    metadata={"case_id": case_id, "score": assessment.score, "risk": assessment.level, "confidence": assessment.confidence},
                )
            self.load_case()
            self.analysis.setPlainText(text)
            self.tabs.setCurrentIndex(6)
        finally:
            self.ai.setEnabled(True)
            self.ai.setText("RUN AI ANALYSIS")

    def replay_timeline(self, index):
        if not self.timeline_events:
            return
        index = min(index, len(self.timeline_events) - 1)
        for item_index in range(self.timeline.count()):
            self.timeline.item(item_index).setHidden(item_index > index)
        item = self.timeline_events[index]
        self.replay_label.setText(f"Replay {index + 1}/{len(self.timeline_events)} - {item['event_type']}: {item['title']}")

    def export_case(self, fmt, ext):
        case_id = self.selected_case_id()
        if not case_id:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export Case", f"blackterm_case_{case_id}{ext}")
        if path:
            try:
                output = write_case_report(self.engine.repository, case_id, path, fmt)
                QMessageBox.information(self, "Case exported", str(output))
            except Exception as exc:
                QMessageBox.critical(self, "Export failed", str(exc))
