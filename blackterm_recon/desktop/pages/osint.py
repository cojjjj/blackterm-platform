from __future__ import annotations

import json
from typing import Any

from PySide6.QtCore import QThread, Qt, Signal
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
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ...intelligence.persistence import persist_intelligence_run
from ..intelligence_worker import IntelligenceWorker
from ..widgets import add_glow


OSINT_MODULES = (
    ("dns", "DNS"),
    ("reverse_dns", "Reverse DNS"),
    ("whois", "WHOIS"),
    ("asn", "ASN / Network"),
    ("geoip", "GeoIP"),
    ("ssl", "TLS Certificate"),
    ("http", "HTTP Headers"),
    ("technology", "Technologies"),
)


class MetricCard(QFrame):
    def __init__(self, label: str, value: str = "--"):
        super().__init__()
        self.setObjectName("panel")
        add_glow(self, blur=14, alpha=20)
        layout = QVBoxLayout(self)
        title = QLabel(label)
        title.setObjectName("muted")
        self.value = QLabel(value)
        self.value.setObjectName("metricValue")
        self.value.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(self.value)

    def set_value(self, value: Any) -> None:
        text = str(value).strip() if value is not None else ""
        self.value.setText(text or "--")


class OSINTPage(QWidget):
    """Standalone, case-aware public-source intelligence workspace."""

    case_created = Signal(int)

    def __init__(self, engine, event_bus=None, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.event_bus = event_bus
        self.thread = None
        self.worker = None
        self.current_result = None
        self.current_case_id = None

        root = QVBoxLayout(self)
        header = QHBoxLayout()
        title_group = QVBoxLayout()
        title = QLabel("BLACKTERM OSINT")
        title.setObjectName("pageTitle")
        subtitle = QLabel(
            "Authorized public-source enrichment with source tracking, evidence capture, and case export."
        )
        subtitle.setObjectName("muted")
        title_group.addWidget(title)
        title_group.addWidget(subtitle)
        header.addLayout(title_group)
        header.addStretch()
        self.status = QLabel("● READY")
        self.status.setObjectName("liveReady")
        header.addWidget(self.status)
        root.addLayout(header)

        launch = QFrame()
        launch.setObjectName("intelligenceLaunch")
        launch_layout = QVBoxLayout(launch)
        target_row = QHBoxLayout()
        self.target = QLineEdit()
        self.target.setPlaceholderText("domain, public IP address, or authorized URL")
        self.target.returnPressed.connect(self.start_collection)
        self.run_button = QPushButton("COLLECT OSINT")
        self.run_button.setObjectName("primary")
        self.run_button.clicked.connect(self.start_collection)
        target_row.addWidget(QLabel("TARGET"))
        target_row.addWidget(self.target, 1)
        target_row.addWidget(self.run_button)
        launch_layout.addLayout(target_row)

        module_row = QHBoxLayout()
        self.checks = {}
        for key, label in OSINT_MODULES:
            check = QCheckBox(label)
            check.setChecked(True)
            self.checks[key] = check
            module_row.addWidget(check)
        module_row.addStretch()
        launch_layout.addLayout(module_row)

        progress_row = QHBoxLayout()
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress_label = QLabel("PIPELINE READY")
        progress_row.addWidget(self.progress, 1)
        progress_row.addWidget(self.progress_label)
        launch_layout.addLayout(progress_row)
        root.addWidget(launch)

        metrics = QGridLayout()
        self.organization = MetricCard("ORGANIZATION")
        self.asn = MetricCard("ASN")
        self.location = MetricCard("LOCATION")
        self.registrar = MetricCard("REGISTRAR")
        self.risk = MetricCard("RISK")
        self.confidence = MetricCard("CONFIDENCE")
        for index, card in enumerate((
            self.organization, self.asn, self.location,
            self.registrar, self.risk, self.confidence,
        )):
            metrics.addWidget(card, index // 3, index % 3)
        root.addLayout(metrics)

        split = QSplitter(Qt.Horizontal)
        root.addWidget(split, 1)

        pipeline_frame = QFrame()
        pipeline_frame.setObjectName("panel")
        pipeline_layout = QVBoxLayout(pipeline_frame)
        pipeline_layout.addWidget(QLabel("SOURCE PIPELINE"))
        self.module_list = QListWidget()
        self._reset_module_list()
        pipeline_layout.addWidget(self.module_list, 1)
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setMaximumHeight(190)
        self.console.setPlaceholderText("Collection events and source notes will appear here.")
        pipeline_layout.addWidget(QLabel("COLLECTION LOG"))
        pipeline_layout.addWidget(self.console)
        split.addWidget(pipeline_frame)

        analysis_frame = QFrame()
        analysis_frame.setObjectName("panel")
        analysis_layout = QVBoxLayout(analysis_frame)
        self.tabs = QTabWidget()
        self.summary = QTextEdit()
        self.summary.setReadOnly(True)
        self.findings = QTextEdit()
        self.findings.setReadOnly(True)
        self.evidence = QTextEdit()
        self.evidence.setReadOnly(True)
        self.raw = QTextEdit()
        self.raw.setReadOnly(True)
        self.tabs.addTab(self.summary, "ANALYST SUMMARY")
        self.tabs.addTab(self.findings, "FINDINGS")
        self.tabs.addTab(self.evidence, "SOURCES / EVIDENCE")
        self.tabs.addTab(self.raw, "RAW JSON")
        analysis_layout.addWidget(self.tabs, 1)

        actions = QHBoxLayout()
        self.save_case = QPushButton("SAVE TO CASE")
        self.save_case.setEnabled(False)
        self.save_case.clicked.connect(self.persist_case)
        self.copy_report = QPushButton("COPY REPORT")
        self.copy_report.setEnabled(False)
        self.copy_report.clicked.connect(self.copy_report_text)
        actions.addWidget(self.save_case)
        actions.addWidget(self.copy_report)
        actions.addStretch()
        analysis_layout.addLayout(actions)
        split.addWidget(analysis_frame)
        split.setSizes([430, 850])

    def _reset_module_list(self) -> None:
        self.module_list.clear()
        for _, label in OSINT_MODULES:
            self.module_list.addItem(f"○  {label:<20} WAITING")

    def start_collection(self) -> None:
        target = self.target.text().strip()
        if not target:
            QMessageBox.warning(self, "OSINT", "Enter a domain, public IP address, or URL.")
            return
        if self.thread is not None:
            return
        enabled = tuple(key for key, _ in OSINT_MODULES if self.checks[key].isChecked())
        if not enabled:
            QMessageBox.warning(self, "OSINT", "Select at least one collection module.")
            return

        self.current_result = None
        self.current_case_id = None
        self.progress.setValue(0)
        self.progress_label.setText("STARTING")
        self.status.setText("● COLLECTING")
        self.run_button.setEnabled(False)
        self.save_case.setEnabled(False)
        self.copy_report.setEnabled(False)
        self.console.clear()
        self.summary.clear()
        self.findings.clear()
        self.evidence.clear()
        self.raw.clear()
        self._reset_module_list()
        for card in (self.organization, self.asn, self.location, self.registrar, self.risk, self.confidence):
            card.set_value("--")

        self.thread = QThread(self)
        self.worker = IntelligenceWorker(target, enabled)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(self.on_progress)
        self.worker.completed.connect(self.on_completed)
        self.worker.failed.connect(self.on_failed)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self._thread_finished)
        self.thread.start()

    def on_progress(self, module: str, percent: int, message: str, result: object) -> None:
        self.progress.setValue(percent)
        self.progress_label.setText(f"{percent}% // {module.upper()}")
        self.console.append(f"[{percent:>3}%] {module.upper():<14} {message}")
        keys = [key for key, _ in OSINT_MODULES]
        if module in keys:
            index = keys.index(module)
            label = OSINT_MODULES[index][1]
            state = "RUNNING" if result is None else str(getattr(result, "status", "complete")).upper()
            icon = "◉" if result is None else "✓" if state == "SUCCESS" else "–" if state == "SKIPPED" else "!"
            self.module_list.item(index).setText(f"{icon}  {label:<20} {state}")

    def on_completed(self, result: object) -> None:
        self.current_result = result
        self.progress.setValue(100)
        self.progress_label.setText("COLLECTION COMPLETE")
        self.status.setText("● COMPLETE")
        self.save_case.setEnabled(True)
        self.copy_report.setEnabled(True)
        self._render_result(result)

    def on_failed(self, message: str) -> None:
        self.status.setText("● ERROR")
        self.progress_label.setText("PIPELINE ERROR")
        QMessageBox.critical(self, "OSINT collection failed", message)

    def _thread_finished(self) -> None:
        self.thread = None
        self.worker = None
        self.run_button.setEnabled(True)

    def _render_result(self, result: object) -> None:
        self.risk.set_value(f"{getattr(result, 'level', '--')} // {getattr(result, 'risk_score', 0)}/100")
        self.confidence.set_value(f"{getattr(result, 'confidence', 0)}%")
        findings = [finding for module in result.modules for finding in module.findings]
        self.organization.set_value(self._first_detail(findings, "Network organization", "Hosting organization"))
        self.asn.set_value(self._first_detail(findings, "Autonomous system"))
        self.location.set_value(self._first_detail(findings, "Approximate location"))
        self.registrar.set_value(self._extract_registrar(result))

        self.summary.setPlainText(result.to_text())
        finding_lines = []
        for module in result.modules:
            for finding in module.findings:
                finding_lines.append(
                    f"[{finding.severity}] {finding.title}\n{finding.detail}\n"
                    f"Source module: {module.module} // Confidence: {finding.confidence}%\n"
                )
        self.findings.setPlainText("\n".join(finding_lines) or "No high-signal findings were produced.")

        evidence_lines = []
        for module in result.modules:
            for item in module.evidence:
                preview = item.content[:1200]
                if len(item.content) > 1200:
                    preview += "\n... [truncated in workspace; complete content remains available to case persistence]"
                evidence_lines.append(
                    f"{item.evidence_type} // {item.title}\nSOURCE: {item.source}\n{preview}\n"
                )
        self.evidence.setPlainText("\n".join(evidence_lines) or "No evidence was collected.")
        self.raw.setPlainText(json.dumps(result.to_dict(), indent=2, default=str))

    @staticmethod
    def _first_detail(findings: list, *titles: str) -> str:
        for title in titles:
            for finding in findings:
                if finding.title == title:
                    return finding.detail
        return "--"

    @staticmethod
    def _extract_registrar(result: object) -> str:
        for module in result.modules:
            if module.module != "whois":
                continue
            text = module.summary
            lower = text.lower()
            if "registrar " in lower:
                start = lower.index("registrar ") + len("registrar ")
                value = text[start:].split(";")[0].strip().rstrip(".")
                return value or "--"
        return "--"

    def persist_case(self) -> None:
        if self.current_result is None:
            return
        try:
            if self.current_case_id is None:
                self.current_case_id = persist_intelligence_run(
                    self.engine.repository, self.current_result
                )
            self.save_case.setText(f"CASE #{self.current_case_id} SAVED")
            self.save_case.setEnabled(False)
            self.case_created.emit(self.current_case_id)
            QMessageBox.information(
                self,
                "OSINT case created",
                f"Collected sources and evidence were saved to case #{self.current_case_id}.",
            )
        except Exception as exc:
            QMessageBox.critical(self, "Case persistence failed", str(exc))

    def copy_report_text(self) -> None:
        if self.current_result is None:
            return
        from PySide6.QtWidgets import QApplication
        QApplication.clipboard().setText(self.current_result.to_text())
        self.copy_report.setText("COPIED")
