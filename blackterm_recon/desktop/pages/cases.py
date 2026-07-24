from __future__ import annotations
from html import escape
from pathlib import Path
from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox, QDialog, QDialogButtonBox, QFormLayout,
    QFileDialog, QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget, QInputDialog,
    QMessageBox, QProgressBar, QPushButton, QSlider, QSplitter, QTabWidget, QTabBar, QTableWidget,
    QTableWidgetItem, QTextBrowser, QTextEdit, QTreeWidget, QTreeWidgetItem, QVBoxLayout,
    QWidget,
)
from ...case_reporting import write_case_report
from ...case_completeness import assess_case_completeness
from ...investigation_engine import assess_case
from ...assistant_engine import (
    answer_case_question, build_case_analyst_brief, investigation_quality,
)
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
        self.ai_chat_history = []
        self.ai_message_records = []
        self.ai_typing_timer = QTimer(self)
        self.ai_typing_timer.timeout.connect(self._typing_tick)
        self.ai_typing_state = None

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
        ai_builder = QPushButton("AI CASE BUILDER")
        ai_builder.setToolTip("Describe or enter an authorized target and launch the autonomous investigation workflow.")
        ai_builder.clicked.connect(self.open_ai_case_builder)
        new = QPushButton("NEW CASE")
        new.setObjectName("primary")
        new.clicked.connect(self.create_case)
        head.addWidget(title)
        head.addStretch()
        head.addWidget(self.search, 1)
        head.addWidget(operator_button)
        head.addWidget(intelligence_button)
        head.addWidget(ai_builder)
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
        overview_tab = QWidget()
        overview_layout = QVBoxLayout(overview_tab)

        completeness_panel = QFrame()
        completeness_panel.setObjectName("panel")
        completeness_layout = QVBoxLayout(completeness_panel)
        completeness_head = QHBoxLayout()
        self.completeness_title = QLabel("CASE INTELLIGENCE SCORE // --")
        self.completeness_title.setObjectName("sectionTitle")
        self.completeness_level = QLabel("SELECT A CASE")
        completeness_head.addWidget(self.completeness_title)
        completeness_head.addStretch()
        completeness_head.addWidget(self.completeness_level)
        completeness_layout.addLayout(completeness_head)

        self.completeness_bar = QProgressBar()
        self.completeness_bar.setRange(0, 100)
        self.completeness_bar.setValue(0)
        self.completeness_bar.setFormat("%p% COMPLETE")
        self.completeness_bar.setTextVisible(True)
        self.completeness_bar.setMinimumHeight(22)
        completeness_layout.addWidget(self.completeness_bar)

        completeness_columns = QHBoxLayout()
        collected_column = QVBoxLayout()
        collected_column.addWidget(QLabel("INTELLIGENCE COLLECTED"))
        self.completeness_collected = QListWidget()
        self.completeness_collected.setMaximumHeight(150)
        collected_column.addWidget(self.completeness_collected)
        missing_column = QVBoxLayout()
        missing_column.addWidget(QLabel("RECOMMENDED NEXT COLLECTION"))
        self.completeness_missing = QListWidget()
        self.completeness_missing.setMaximumHeight(150)
        missing_column.addWidget(self.completeness_missing)
        completeness_columns.addLayout(collected_column, 1)
        completeness_columns.addLayout(missing_column, 1)
        completeness_layout.addLayout(completeness_columns)
        overview_layout.addWidget(completeness_panel)

        self.overview = QTextEdit()
        self.overview.setReadOnly(True)
        overview_layout.addWidget(self.overview, 1)
        self.tabs.addTab(overview_tab, "OVERVIEW")

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

        analyst_metrics = QHBoxLayout()
        self.ai_risk = QLabel("RISK // --")
        self.ai_confidence = QLabel("CONFIDENCE // --")
        self.ai_evidence = QLabel("EVIDENCE // --")
        self.ai_quality = QLabel("QUALITY // --")
        self.ai_status = QLabel("STATUS // AWAITING ANALYSIS")
        for metric in (self.ai_risk, self.ai_confidence, self.ai_evidence, self.ai_quality, self.ai_status):
            metric.setObjectName("sectionTitle")
            analyst_metrics.addWidget(metric)
        analyst_metrics.addStretch()
        analyst_layout.addLayout(analyst_metrics)

        self.ai_progress = QProgressBar()
        self.ai_progress.setRange(0, 100)
        self.ai_progress.setValue(0)
        self.ai_progress.setFormat("AI ANALYST READY")
        self.ai_progress.setMinimumHeight(22)
        analyst_layout.addWidget(self.ai_progress)

        meter_row = QHBoxLayout()
        self.ai_risk_meter = QProgressBar()
        self.ai_risk_meter.setFormat("RISK %p%")
        self.ai_confidence_meter = QProgressBar()
        self.ai_confidence_meter.setFormat("CONFIDENCE %p%")
        self.ai_quality_meter = QProgressBar()
        self.ai_quality_meter.setFormat("INVESTIGATION QUALITY %p%")
        for meter in (self.ai_risk_meter, self.ai_confidence_meter, self.ai_quality_meter):
            meter.setRange(0, 100)
            meter.setValue(0)
            meter.setMinimumHeight(20)
            meter_row.addWidget(meter, 1)
        analyst_layout.addLayout(meter_row)

        self.ai_context = QLabel("AI MEMORY // CASE --  •  SCANS 0  •  EVIDENCE 0  •  NOTES 0  •  TIMELINE 0")
        self.ai_context.setObjectName("muted")
        analyst_layout.addWidget(self.ai_context)

        analyst_split = QSplitter(Qt.Horizontal)
        self.analysis = QTextEdit()
        self.analysis.setReadOnly(True)
        self.analysis.setPlaceholderText("Run AI Analysis to build a grounded case assessment.")
        analyst_split.addWidget(self.analysis)

        finding_panel = QFrame()
        finding_panel.setObjectName("panel")
        finding_layout = QVBoxLayout(finding_panel)
        finding_title = QLabel("EXPLAINABLE FINDINGS")
        finding_title.setObjectName("sectionTitle")
        finding_layout.addWidget(finding_title)
        self.ai_findings = QListWidget()
        finding_layout.addWidget(self.ai_findings, 1)
        explain = QPushButton("EXPLAIN SELECTED FINDING")
        explain.clicked.connect(self.explain_selected_finding)
        finding_layout.addWidget(explain)
        self.ai_explanation = QTextEdit()
        self.ai_explanation.setReadOnly(True)
        self.ai_explanation.setMaximumHeight(190)
        self.ai_explanation.setPlaceholderText("Select a finding to see why it matters and what to validate.")
        finding_layout.addWidget(self.ai_explanation)
        analyst_split.addWidget(finding_panel)
        analyst_split.setSizes([700, 390])
        analyst_layout.addWidget(analyst_split, 1)

        suggestion_title = QLabel("SUGGESTED QUESTIONS")
        suggestion_title.setObjectName("sectionTitle")
        analyst_layout.addWidget(suggestion_title)
        suggestion_row = QHBoxLayout()
        self.ai_suggestion_buttons = []
        for question in (
            "Summarize this case",
            "Why is this risky?",
            "What changed?",
            "What should I do next?",
            "Explain every open port",
        ):
            button = QPushButton(question)
            button.setToolTip(question)
            button.clicked.connect(lambda checked=False, text=question: self.ask_suggested_question(text))
            self.ai_suggestion_buttons.append(button)
            suggestion_row.addWidget(button)
        analyst_layout.addLayout(suggestion_row)

        chat_title = QLabel("BLACKTERM AI CONVERSATION")
        chat_title.setObjectName("sectionTitle")
        analyst_layout.addWidget(chat_title)
        self.ai_response = QTextBrowser()
        self.ai_response.setOpenExternalLinks(False)
        self.ai_response.anchorClicked.connect(self.open_ai_evidence_reference)
        self.ai_response.setMinimumHeight(190)
        self.ai_response.setPlaceholderText("Ask a case question. Every answer will show its supporting evidence references.")
        analyst_layout.addWidget(self.ai_response, 1)

        ask_row = QHBoxLayout()
        self.ai_question = QLineEdit()
        self.ai_question.setPlaceholderText("Ask about this case, its evidence, risk, changes, ports, or next actions...")
        self.ai_question.returnPressed.connect(self.ask_ai_question)
        self.ask_button = QPushButton("ASK AI ANALYST")
        self.ask_button.setObjectName("primary")
        self.ask_button.clicked.connect(self.ask_ai_question)
        copy_button = QPushButton("COPY EXECUTIVE BRIEF")
        copy_button.clicked.connect(self.copy_ai_brief)
        ask_row.addWidget(self.ai_question, 1)
        ask_row.addWidget(self.ask_button)
        ask_row.addWidget(copy_button)
        analyst_layout.addLayout(ask_row)
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

    def open_ai_case_builder(self):
        target, accepted = QInputDialog.getText(
            self,
            "BLACKTERM AI Case Builder",
            "Enter an authorized domain, IP address, or hostname.\n\nBLACKTERM will open the autonomous workflow with the target preloaded.",
        )
        target = target.strip()
        if not accepted or not target:
            return
        window = self.window()
        starter = getattr(window, "start_new_investigation", None)
        if callable(starter):
            starter(prefill_target=target, ai_mode=True)
            return
        self.open_intelligence_engine()
        self.intelligence_page.target.setText(target)
        QMessageBox.information(
            self,
            "AI Case Builder",
            "The target was loaded into Live Investigation. Confirm authorization and start the workflow.",
        )

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
        self.update_case_completeness(case, scans, notes, evidence, self.timeline_events)
        self.clear_correlation()

    def update_case_completeness(self, case, scans, notes, evidence, timeline):
        report = assess_case_completeness(case, scans, notes, evidence, timeline)
        self.completeness_title.setText(f"CASE INTELLIGENCE SCORE // {report.score}/100")
        self.completeness_level.setText(report.level)
        self.completeness_bar.setValue(report.score)

        if report.score >= 85:
            accent = "#36e6b0"
        elif report.score >= 65:
            accent = "#31b7ff"
        elif report.score >= 40:
            accent = "#f5c451"
        else:
            accent = "#ff8a4c"
        self.completeness_bar.setStyleSheet(
            "QProgressBar{border:1px solid #31587a;border-radius:8px;background:#06111f;"
            "text-align:center;color:#e8f5ff;font-weight:700;}"
            f"QProgressBar::chunk{{border-radius:7px;background:{accent};}}"
        )
        self.completeness_level.setStyleSheet(f"color:{accent};font-weight:700;")

        self.completeness_collected.clear()
        for check in report.collected:
            self.completeness_collected.addItem(f"✓  {check.label}  (+{check.weight})")
        if not report.collected:
            self.completeness_collected.addItem("No intelligence collected yet.")

        self.completeness_missing.clear()
        for check in report.missing:
            self.completeness_missing.addItem(f"•  {check.label} — {check.detail}")
        if not report.missing:
            self.completeness_missing.addItem("✓ Case collection objectives complete.")

    def clear_correlation(self):
        self.correlation_report = None
        self.ai_chat_history = []
        self.ai_message_records = []
        self.ai_typing_timer = QTimer(self)
        self.ai_typing_timer.timeout.connect(self._typing_tick)
        self.ai_typing_state = None
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
        self.tabs.setCurrentIndex(6)
        self.ai_progress.setValue(8)
        self.ai_progress.setFormat("REVIEWING SAVED EVIDENCE...")
        self.analysis.clear()
        self.ai_response.clear()
        stages = [
            (24, "CORRELATING PORTS AND SERVICES..."),
            (43, "ASSESSING EXPOSURE CONTEXT..."),
            (62, "COMPARING INVESTIGATION HISTORY..."),
            (81, "BUILDING RECOMMENDATIONS..."),
        ]
        for delay, (value, label) in enumerate(stages, start=1):
            QTimer.singleShot(delay * 140, lambda v=value, text=label: self._set_ai_stage(v, text))
        QTimer.singleShot(760, lambda cid=case_id: self._complete_ai_analysis(cid))

    def _set_ai_stage(self, value, label):
        self.ai_progress.setValue(value)
        self.ai_progress.setFormat(label)

    def _complete_ai_analysis(self, case_id):
        try:
            brief = build_case_analyst_brief(self.engine.repository, case_id)
            self.current_ai_brief = brief
            self.render_ai_brief(brief)
            text = brief.to_text()
            self.engine.repository.add_case_evidence(case_id, "AI", "AI analyst investigation brief", "BLACKTERM AI Analyst", text)
            self.engine.repository.add_case_timeline(case_id, "AI", "AI analyst investigation completed", f"{brief.risk_level} risk / {brief.confidence}% confidence")
            if self.event_bus:
                from ...events import EventLevel
                self.event_bus.emit(
                    "case", brief.assessment, title="AI Analyst Complete", level=EventLevel.AI, module="cases",
                    metadata={"case_id": case_id, "score": brief.risk_score, "risk": brief.risk_level, "confidence": brief.confidence},
                )
            self.ai_progress.setValue(100)
            self.ai_progress.setFormat("ANALYSIS COMPLETE")
        except Exception as exc:
            self.ai_progress.setValue(0)
            self.ai_progress.setFormat("ANALYSIS FAILED")
            QMessageBox.critical(self, "AI analysis failed", str(exc))
        finally:
            self.ai.setEnabled(True)
            self.ai.setText("RUN AI ANALYSIS")

    def render_ai_brief(self, brief):
        accent = "#36e6b0" if brief.risk_score < 25 else "#f5c451" if brief.risk_score < 55 else "#ff6b8a"
        self.ai_risk.setText(f"RISK // {brief.risk_level} {brief.risk_score}/100")
        self.ai_risk.setStyleSheet(f"color:{accent};font-weight:800;")
        self.ai_confidence.setText(f"CONFIDENCE // {brief.confidence}%")
        self.ai_evidence.setText(f"EVIDENCE // {brief.evidence_count} SIGNALS")
        quality, _ = investigation_quality(self.engine.repository, brief.case_id)
        self.ai_quality.setText(f"QUALITY // {quality}%")
        self.ai_status.setText(f"STATUS // {brief.status}")
        self.ai_risk_meter.setValue(brief.risk_score)
        self.ai_confidence_meter.setValue(brief.confidence)
        self.ai_quality_meter.setValue(quality)
        scans = self.engine.repository.case_scans(brief.case_id)
        evidence_items = self.engine.repository.case_evidence(brief.case_id)
        notes = self.engine.repository.case_notes(brief.case_id)
        timeline = self.engine.repository.case_timeline(brief.case_id)
        self.ai_context.setText(
            f"AI MEMORY // CASE {brief.case_id}  •  SCANS {len(scans)}  •  EVIDENCE {len(evidence_items)}  "
            f"•  NOTES {len(notes)}  •  TIMELINE {len(timeline)}"
        )
        facts = "".join(f"<li>{item}</li>" for item in brief.facts)
        inferences = "".join(f"<li>{item}</li>" for item in brief.inferences)
        memory = "".join(f"<li>{item}</li>" for item in brief.memory)
        actions = "".join(f"<li>{item}</li>" for item in brief.recommendations)
        html = (
            '<h2 style="color:#31b7ff;">BLACKTERM AI ANALYST</h2>'
            f'<h3 style="color:#e8f5ff;">Assessment</h3><p>{brief.assessment}</p>'
            f'<h3 style="color:#36e6b0;">Confirmed Facts</h3><ul>{facts}</ul>'
            f'<h3 style="color:#f5c451;">Analyst Assessment</h3><ul>{inferences}</ul>'
            f'<h3 style="color:#c45cff;">Investigation Memory</h3><ul>{memory}</ul>'
            f'<h3 style="color:#31b7ff;">Recommended Actions</h3><ol>{actions}</ol>'
            '<p style="color:#8da6bd;"><b>Advisory:</b> Exposure is not proof of exploitability. Validate conclusions with authorized evidence.</p>'
        )
        self.analysis.setHtml(html)
        self.ai_findings.clear()
        for finding in brief.findings:
            self.ai_findings.addItem(finding)
        if self.ai_findings.count():
            self.ai_findings.setCurrentRow(0)
        self._reset_ai_conversation(brief)

    def _reset_ai_conversation(self, brief):
        self.ai_chat_history = []
        self.ai_message_records = []
        self.ai_response.clear()
        welcome = (
            f"Case #{brief.case_id} is loaded with {brief.evidence_count} evidence signal(s). "
            "Ask a question and BLACKTERM will separate saved observations from analyst interpretation."
        )
        self._append_ai_message("BLACKTERM AI", welcome, brief.confidence, ["Current case assessment"])

    def _message_card(self, record):
        speaker = record["speaker"]
        body = record["display_body"]
        confidence = record.get("confidence")
        refs = record.get("evidence_refs") or []
        is_operator = speaker.upper() == "OPERATOR"
        accent = "#31b7ff" if is_operator else "#36e6b0"
        background = "#0c1d2c" if is_operator else "#101426"
        alignment = "margin-left:9%;" if is_operator else "margin-right:9%;"
        safe_body = escape(str(body)).replace("\n", "<br>")
        meta = ""
        if confidence is not None:
            meta += f'<span style="color:#c45cff;"><b>Confidence:</b> {int(confidence)}%</span>'
        if refs:
            links = []
            for index, item in enumerate(refs):
                links.append(
                    f'<a href="evidence://{index}" style="color:#8fd8ff;text-decoration:none;">{escape(str(item))}</a>'
                )
            separator = " &nbsp; | &nbsp; " if meta else ""
            meta += separator + '<span style="color:#8da6bd;"><b>Evidence:</b> ' + " • ".join(links) + "</span>"
        avatar = "TYLER" if is_operator else "BLACKTERM AI"
        return (
            f'<div style="{alignment}background:{background};border:1px solid #214764;border-radius:12px;'
            'padding:12px;margin:8px 3px;">'
            f'<div style="color:{accent};font-weight:800;margin-bottom:7px;">{avatar}</div>'
            f'<div style="color:#e8f5ff;line-height:1.42;">{safe_body}</div>'
            + (f'<div style="margin-top:9px;font-size:11px;">{meta}</div>' if meta else "")
            + '</div>'
        )

    def _render_ai_conversation(self):
        self.ai_response.setHtml("".join(self._message_card(record) for record in self.ai_message_records))
        scrollbar = self.ai_response.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _append_ai_message(self, speaker, body, confidence=None, evidence_refs=None, animate=False):
        record = {
            "speaker": speaker,
            "body": str(body),
            "display_body": "" if animate else str(body),
            "confidence": confidence,
            "evidence_refs": [str(item) for item in (evidence_refs or []) if item],
        }
        self.ai_message_records.append(record)
        self.ai_chat_history.append((speaker, body))
        self._render_ai_conversation()
        if animate:
            self.ai_typing_state = {"record": record, "position": 0}
            self.ai_typing_timer.start(18)

    def _typing_tick(self):
        state = self.ai_typing_state
        if not state:
            self.ai_typing_timer.stop()
            return
        record = state["record"]
        full = record["body"]
        position = min(len(full), state["position"] + 5)
        state["position"] = position
        record["display_body"] = full[:position] + ("▌" if position < len(full) else "")
        self._render_ai_conversation()
        if position >= len(full):
            record["display_body"] = full
            self.ai_typing_timer.stop()
            self.ai_typing_state = None
            self.ai_progress.setValue(100)
            self.ai_progress.setFormat("RESPONSE COMPLETE")
            self.ai_question.setEnabled(True)
            self.ask_button.setEnabled(True)
            self.ai_question.setFocus()
            self._render_ai_conversation()

    def open_ai_evidence_reference(self, url: QUrl):
        scheme = url.scheme().lower()
        if scheme == "evidence":
            self.tabs.setCurrentIndex(2)
            if self.evidence.rowCount():
                self.evidence.selectRow(0)
        elif scheme == "scan":
            self.tabs.setCurrentIndex(0)
        else:
            self.tabs.setCurrentIndex(3)

    def ask_suggested_question(self, question):
        self.ai_question.setText(question)
        self.ask_ai_question()

    def explain_selected_finding(self):
        item = self.ai_findings.currentItem()
        case_id = self.selected_case_id()
        if not item or not case_id:
            return
        reply = answer_case_question(f"explain {item.text()}", self.engine.repository, case_id)
        self.ai_explanation.setPlainText(reply.body)

    def ask_ai_question(self):
        case_id = self.selected_case_id()
        question = self.ai_question.text().strip()
        if not case_id or not question or self.ai_typing_timer.isActive():
            return
        self._append_ai_message("OPERATOR", question)
        self.ai_question.clear()
        self.ai_question.setEnabled(False)
        self.ask_button.setEnabled(False)
        stages = [
            (18, "REVIEWING SAVED EVIDENCE..."),
            (39, "CORRELATING CASE HISTORY..."),
            (61, "CHECKING SUPPORTING SIGNALS..."),
            (82, "BUILDING GROUNDED RESPONSE..."),
        ]
        for delay, (value, label) in enumerate(stages):
            QTimer.singleShot(delay * 90, lambda v=value, text=label: self._set_ai_stage(v, text))
        QTimer.singleShot(430, lambda q=question, cid=case_id: self._finish_ai_question(q, cid))

    def _finish_ai_question(self, question, case_id):
        try:
            reply = answer_case_question(question, self.engine.repository, case_id)
            body = f"{reply.title}\n\n{reply.body}"
            self._append_ai_message("BLACKTERM AI", body, reply.confidence, reply.evidence_refs, animate=True)
            for index, text in enumerate(reply.suggestions[:len(self.ai_suggestion_buttons)]):
                button = self.ai_suggestion_buttons[index]
                button.setText(text)
                button.setToolTip(text)
                try:
                    button.clicked.disconnect()
                except (RuntimeError, TypeError):
                    pass
                button.clicked.connect(lambda checked=False, value=text: self.ask_suggested_question(value))
        except Exception as exc:
            self._append_ai_message("BLACKTERM AI", f"The case question could not be answered: {exc}", 0, [], animate=True)

    def copy_ai_brief(self):
        case_id = self.selected_case_id()
        if not case_id:
            return
        brief = getattr(self, "current_ai_brief", None) or build_case_analyst_brief(self.engine.repository, case_id)
        from PySide6.QtWidgets import QApplication
        QApplication.clipboard().setText(brief.to_text())
        self._append_ai_message("BLACKTERM AI", "Executive brief copied to the clipboard.", brief.confidence, ["Current case assessment"])

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
