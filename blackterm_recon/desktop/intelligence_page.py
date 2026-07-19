from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QThread, Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from ..correlation_engine import correlate_case
from ..intelligence.persistence import persist_intelligence_run
from .intelligence_worker import IntelligenceWorker
from .investigation_graph import InvestigationGraph
from .live_widgets import AnimatedNumberLabel, StageSequence, TypingTextEdit


MODULES = (
    ("dns", "DNS"),
    ("reverse_dns", "Reverse DNS"),
    ("whois", "WHOIS"),
    ("ssl", "SSL / TLS"),
    ("http", "HTTP Headers"),
    ("technology", "Technologies"),
)


class IntelligencePage(QWidget):
    case_created = Signal(int)
    live_event = Signal(str, str)

    def __init__(self, engine, event_bus=None, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.event_bus = event_bus
        self.thread = None
        self.worker = None
        self.current_result = None
        self.current_case_id = None
        self.completed_modules = 0
        self.finding_total = 0
        self.evidence_total = 0
        self.relationship_total = 0
        self.module_states: dict[str, str] = {}
        self.stage_sequence = StageSequence(self)
        self.stage_sequence.stage_started.connect(self._stage_started)
        self.stage_sequence.stage_finished.connect(self._stage_finished)
        self.stage_sequence.sequence_finished.connect(self._finish_live_sequence)

        root = QVBoxLayout(self)
        header = QHBoxLayout()
        title_group = QVBoxLayout()
        title = QLabel("BLACKTERM Intelligence Engine")
        title.setObjectName("pageTitle")
        subtitle = QLabel(
            "LIVE INVESTIGATION MODE // coordinated collection, evidence, correlation, and graph."
        )
        subtitle.setObjectName("muted")
        title_group.addWidget(title)
        title_group.addWidget(subtitle)
        header.addLayout(title_group)
        header.addStretch()
        self.live_indicator = QLabel("● LIVE MODE READY")
        self.live_indicator.setObjectName("liveReady")
        header.addWidget(self.live_indicator)
        root.addLayout(header)

        launch = QFrame()
        launch.setObjectName("intelligenceLaunch")
        launch_layout = QVBoxLayout(launch)
        target_row = QHBoxLayout()
        self.target = QLineEdit()
        self.target.setPlaceholderText("domain, IP address, or authorized URL")
        self.target.returnPressed.connect(self.start_run)
        self.run_button = QPushButton("RUN LIVE INVESTIGATION")
        self.run_button.setObjectName("primary")
        self.run_button.clicked.connect(self.start_run)
        target_row.addWidget(QLabel("TARGET"))
        target_row.addWidget(self.target, 1)
        target_row.addWidget(self.run_button)
        launch_layout.addLayout(target_row)

        module_row = QHBoxLayout()
        self.checks = {}
        for key, label in MODULES:
            check = QCheckBox(label)
            check.setChecked(True)
            self.checks[key] = check
            module_row.addWidget(check)
        module_row.addStretch()
        launch_layout.addLayout(module_row)

        progress_row = QHBoxLayout()
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress_label = QLabel("PIPELINE READY")
        progress_row.addWidget(self.progress, 1)
        progress_row.addWidget(self.progress_label)
        launch_layout.addLayout(progress_row)
        root.addWidget(launch)

        telemetry = QFrame()
        telemetry.setObjectName("intelligenceTelemetry")
        telemetry_layout = QGridLayout(telemetry)
        self.modules_metric = AnimatedNumberLabel(0)
        self.findings_metric = AnimatedNumberLabel(0)
        self.evidence_metric = AnimatedNumberLabel(0)
        self.relationships_metric = AnimatedNumberLabel(0)
        for widget in (
            self.modules_metric,
            self.findings_metric,
            self.evidence_metric,
            self.relationships_metric,
        ):
            widget.setObjectName("metricValue")
        telemetry_layout.addWidget(QLabel("MODULES COMPLETE"), 0, 0)
        telemetry_layout.addWidget(QLabel("FINDINGS"), 0, 1)
        telemetry_layout.addWidget(QLabel("EVIDENCE"), 0, 2)
        telemetry_layout.addWidget(QLabel("RELATIONSHIPS"), 0, 3)
        telemetry_layout.addWidget(self.modules_metric, 1, 0)
        telemetry_layout.addWidget(self.findings_metric, 1, 1)
        telemetry_layout.addWidget(self.evidence_metric, 1, 2)
        telemetry_layout.addWidget(self.relationships_metric, 1, 3)
        root.addWidget(telemetry)

        split = QSplitter(Qt.Horizontal)
        root.addWidget(split, 1)

        left = QFrame()
        left.setObjectName("intelligencePipeline")
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(QLabel("LIVE MODULE PIPELINE"))
        self.module_list = QListWidget()
        for key, label in MODULES:
            self.module_list.addItem(f"○  {label:<18} WAITING")
        left_layout.addWidget(self.module_list, 1)
        left_layout.addWidget(QLabel("LIVE INTELLIGENCE CONSOLE"))
        self.live_output = TypingTextEdit()
        self.live_output.setReadOnly(True)
        self.live_output.setMaximumHeight(250)
        left_layout.addWidget(self.live_output)
        split.addWidget(left)

        right = QFrame()
        right.setObjectName("intelligenceAnalysis")
        right_layout = QVBoxLayout(right)
        score_grid = QGridLayout()
        self.priority = QLabel("--")
        self.score = QLabel("--")
        self.confidence = QLabel("--")
        self.case_value = QLabel("--")
        for widget in (self.priority, self.score, self.confidence, self.case_value):
            widget.setObjectName("metricValue")
        score_grid.addWidget(QLabel("PRIORITY"), 0, 0)
        score_grid.addWidget(QLabel("RISK SCORE"), 0, 1)
        score_grid.addWidget(QLabel("CONFIDENCE"), 0, 2)
        score_grid.addWidget(QLabel("CASE"), 0, 3)
        score_grid.addWidget(self.priority, 1, 0)
        score_grid.addWidget(self.score, 1, 1)
        score_grid.addWidget(self.confidence, 1, 2)
        score_grid.addWidget(self.case_value, 1, 3)
        right_layout.addLayout(score_grid)

        self.summary = TypingTextEdit()
        self.summary.setReadOnly(True)
        self.summary.setPlaceholderText("Live analyst output will appear here.")
        self.summary.doubleClicked = self.summary.finish_typing
        right_layout.addWidget(self.summary, 1)

        actions = QHBoxLayout()
        self.open_case = QPushButton("OPEN CASE")
        self.open_case.setEnabled(False)
        self.open_case.clicked.connect(self.emit_case)
        self.correlate = QPushButton("BUILD LIVE GRAPH")
        self.correlate.setEnabled(False)
        self.correlate.clicked.connect(self.build_graph_live)
        actions.addWidget(self.open_case)
        actions.addWidget(self.correlate)
        actions.addStretch()
        right_layout.addLayout(actions)
        split.addWidget(right)
        split.setSizes([430, 850])

        self.graph = InvestigationGraph()
        self.graph.setVisible(False)
        root.addWidget(self.graph, 1)

    def selected_modules(self):
        return tuple(key for key, check in self.checks.items() if check.isChecked())

    def start_run(self):
        target = self.target.text().strip()
        if not target:
            QMessageBox.warning(self, "Target required", "Enter an authorized target first.")
            return
        enabled = self.selected_modules()
        if not enabled:
            QMessageBox.warning(self, "Modules required", "Enable at least one module.")
            return

        self.stage_sequence.stop()
        self.current_result = None
        self.current_case_id = None
        self.completed_modules = 0
        self.finding_total = 0
        self.evidence_total = 0
        self.relationship_total = 0
        self.graph.setVisible(False)
        self.graph.clear_graph()
        self.open_case.setEnabled(False)
        self.correlate.setEnabled(False)
        self.run_button.setEnabled(False)
        self.run_button.setText("INVESTIGATION LIVE…")
        self.live_indicator.setObjectName("liveActive")
        self.live_indicator.style().unpolish(self.live_indicator)
        self.live_indicator.style().polish(self.live_indicator)
        self.live_indicator.setText("● LIVE INVESTIGATION ACTIVE")
        self.progress.setValue(0)
        self.progress_label.setText("INITIALIZING")
        self.live_output.clear()
        self.summary.clear()
        self.priority.setText("--")
        self.score.setText("--")
        self.confidence.setText("--")
        self.case_value.setText("--")
        for counter in (
            self.modules_metric,
            self.findings_metric,
            self.evidence_metric,
            self.relationships_metric,
        ):
            counter.set_value(0, animate=False)
        self._reset_module_rows(enabled)
        self._append_console(
            "BLACKTERM LIVE INVESTIGATION\n"
            f"Target: {target}\n"
            "Initializing intelligence pipeline...\n"
        )
        self._emit_live_event("Investigation Started", f"Live collection started for {target}.")

        self.thread = QThread(self)
        self.worker = IntelligenceWorker(target, enabled)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(self.on_progress)
        self.worker.completed.connect(self.on_completed)
        self.worker.failed.connect(self.on_failed)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.finished.connect(self._thread_finished)
        self.thread.start()

    def _reset_module_rows(self, enabled):
        self.module_states = {}
        for index, (key, label) in enumerate(MODULES):
            state = "QUEUED" if key in enabled else "DISABLED"
            icon = "○" if key in enabled else "—"
            self.module_states[key] = state
            self.module_list.item(index).setText(f"{icon}  {label:<18} {state}")

    def _row_for(self, module):
        for index, (key, _) in enumerate(MODULES):
            if key == module:
                return index
        return -1

    def _append_console(self, message):
        current = self.live_output.toPlainText()
        stamp = datetime.now().strftime("%H:%M:%S")
        block = f"{current}\n[{stamp}] {message}".strip()
        self.live_output.setPlainText(block)
        self.live_output.ensureCursorVisible()

    def on_progress(self, module, percent, message, module_result):
        self.progress.setValue(percent)
        self.progress_label.setText(f"{module.upper()} // {percent}%")
        row = self._row_for(module)

        if row >= 0 and module_result is None:
            self.module_states[module] = "RUNNING"
            self.module_list.item(row).setText(f"◆  {MODULES[row][1]:<18} RUNNING")

        if row >= 0 and module_result is not None:
            icon = (
                "✓" if module_result.status == "success"
                else "—" if module_result.status == "skipped"
                else "!"
            )
            self.module_states[module] = module_result.status.upper()
            self.module_list.item(row).setText(
                f"{icon}  {MODULES[row][1]:<18} {module_result.status.upper()}"
            )
            self.completed_modules += 1
            self.finding_total += len(module_result.findings)
            self.evidence_total += len(module_result.evidence)
            self.relationship_total += len(module_result.relationships)
            self.modules_metric.set_value(self.completed_modules)
            self.findings_metric.set_value(self.finding_total)
            self.evidence_metric.set_value(self.evidence_total)
            self.relationships_metric.set_value(self.relationship_total)
            self._emit_live_event(
                f"{module.upper()} {module_result.status.upper()}",
                module_result.summary,
            )

        self._append_console(f"{module.upper():<14} {message}")

    def on_completed(self, result):
        self.current_result = result
        self.progress.setValue(100)
        self.progress_label.setText("PERSISTING INVESTIGATION")
        self.priority.setText(result.level)
        self.score.setText(f"{result.risk_score}/100")
        self.confidence.setText(f"{result.confidence}%")

        try:
            self.current_case_id = persist_intelligence_run(
                self.engine.repository, result
            )
            self.case_value.setText(f"#{self.current_case_id}")
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Persistence warning",
                f"The run completed, but case persistence failed:\n{exc}",
            )

        self.open_case.setEnabled(self.current_case_id is not None)
        self.correlate.setEnabled(self.current_case_id is not None)
        self._append_console(
            f"Evidence persisted. Case #{self.current_case_id} ready."
            if self.current_case_id else "Collection complete."
        )
        self._emit_live_event(
            "Evidence Persisted",
            f"{result.evidence_count} evidence item(s) saved.",
        )

        stages = [
            ("evidence", "Evidence persisted", 320),
            ("correlation", "Correlating intelligence", 520),
            ("graph", "Constructing live graph", 540),
            ("analysis", "AI analyst synthesizing findings", 650),
            ("complete", "Investigation complete", 500),
        ]
        self.stage_sequence.start(stages)

    def _stage_started(self, key, label, index):
        percentages = {
            "evidence": 92,
            "correlation": 94,
            "graph": 96,
            "analysis": 98,
            "complete": 100,
        }
        self.progress.setValue(percentages.get(key, 100))
        self.progress_label.setText(label.upper())
        self._append_console(label + "…")
        if key == "correlation" and self.current_case_id:
            try:
                report = correlate_case(self.engine.repository, self.current_case_id)
                self.relationship_total = len(report.edges)
                self.relationships_metric.set_value(self.relationship_total)
                self._pending_report = report
            except Exception as exc:
                self._pending_report = None
                self._append_console(f"Correlation warning: {exc}")
        elif key == "graph" and getattr(self, "_pending_report", None):
            self.graph.setVisible(True)
            self.graph.set_report_live(self._pending_report, interval_ms=170)
        elif key == "analysis" and self.current_result:
            preface = (
                "BLACKTERM AI ANALYST\n\n"
                "Analyzing collected evidence...\n"
                "Cross-checking module findings...\n"
                "Correlating infrastructure relationships...\n\n"
            )
            self.summary.type_text(
                preface + self.current_result.to_text(),
                interval_ms=5,
                chunk_size=3,
            )

    def _stage_finished(self, key, label, index):
        self._emit_live_event(label.title(), "Stage completed.")

    def _finish_live_sequence(self):
        self.progress.setValue(100)
        self.progress_label.setText("INVESTIGATION COMPLETE")
        self.live_indicator.setObjectName("liveComplete")
        self.live_indicator.style().unpolish(self.live_indicator)
        self.live_indicator.style().polish(self.live_indicator)
        self.live_indicator.setText("● INVESTIGATION COMPLETE")
        self._append_console("BLACKTERM investigation complete.")
        self._emit_live_event(
            "Investigation Complete",
            self.current_result.summary if self.current_result else "Pipeline complete.",
        )
        self._emit_platform_event()
        QTimer.singleShot(1600, self._restore_live_ready)

    def _restore_live_ready(self):
        self.live_indicator.setObjectName("liveReady")
        self.live_indicator.style().unpolish(self.live_indicator)
        self.live_indicator.style().polish(self.live_indicator)
        self.live_indicator.setText("● LIVE MODE READY")

    def _emit_platform_event(self):
        if not self.event_bus or not self.current_result:
            return
        try:
            from ..events import EventLevel
            self.event_bus.emit(
                "intelligence",
                self.current_result.summary,
                title="Live Investigation Complete",
                level=EventLevel.AI,
                module="intelligence",
                metadata={
                    "case_id": self.current_case_id,
                    "target": self.current_result.normalized_target,
                    "score": self.current_result.risk_score,
                    "confidence": self.current_result.confidence,
                    "evidence": self.current_result.evidence_count,
                    "relationships": self.relationship_total,
                },
            )
        except Exception:
            pass

    def _emit_live_event(self, title, message):
        self.live_event.emit(title, message)
        if not self.event_bus:
            return
        try:
            from ..events import EventLevel
            self.event_bus.emit(
                "live_investigation",
                message,
                title=title,
                level=EventLevel.INFO,
                module="intelligence-live",
                metadata={"case_id": self.current_case_id},
            )
        except Exception:
            pass

    def on_failed(self, message):
        self.stage_sequence.stop()
        QMessageBox.critical(self, "Live investigation failed", message)
        self._append_console(f"ERROR: {message}")
        self.progress_label.setText("INVESTIGATION FAILED")
        self.live_indicator.setText("● LIVE MODE ERROR")

    def _thread_finished(self):
        self.run_button.setEnabled(True)
        self.run_button.setText("RUN LIVE INVESTIGATION")
        self.thread = None
        self.worker = None

    def build_graph_live(self):
        if not self.current_case_id:
            return
        report = correlate_case(self.engine.repository, self.current_case_id)
        self.relationship_total = len(report.edges)
        self.relationships_metric.set_value(self.relationship_total)
        self.graph.setVisible(True)
        self.graph.set_report_live(report, interval_ms=150)
        self._append_console(
            f"Live graph build started: {len(report.nodes)} nodes / {len(report.edges)} links."
        )

    def emit_case(self):
        if self.current_case_id:
            self.case_created.emit(self.current_case_id)
