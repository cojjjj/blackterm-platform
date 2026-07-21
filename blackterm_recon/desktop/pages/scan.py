from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QProgressBar, QPushButton, QTableWidget,
    QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget
)

from ...ports import parse_ports
from ...profiles import SCAN_PROFILES, get_profile
from ...summary import build_summary
from ...attack_surface import build_attack_surface
from ..workers import ScanWorker


class ScanPage(QWidget):
    scan_started = Signal(str)
    scan_port_observed = Signal(str, object)
    scan_completed = Signal(int, object)

    def __init__(self, engine):
        super().__init__()
        self.engine = engine
        self.thread = None
        self.worker = None
        root = QVBoxLayout(self)

        title = QLabel("Authorized Assessment")
        title.setObjectName("pageTitle")
        subtitle = QLabel(
            "Profile-driven TCP visibility for systems you own or are explicitly authorized to test."
        )
        subtitle.setObjectName("muted")
        root.addWidget(title)
        root.addWidget(subtitle)

        controls = QFrame()
        controls.setObjectName("panel")
        grid = QGridLayout(controls)
        grid.addWidget(QLabel("TARGET"), 0, 0)
        grid.addWidget(QLabel("PROFILE"), 0, 1)
        grid.addWidget(QLabel("PORTS"), 0, 2)

        self.target = QLineEdit("127.0.0.1")
        self.target.setPlaceholderText("IP address or hostname")

        self.profile = QComboBox()
        for key, profile in SCAN_PROFILES.items():
            self.profile.addItem(profile.name, key)
        self.profile.setCurrentIndex(self.profile.findData("standard"))
        self.profile.currentIndexChanged.connect(self.apply_profile)

        self.ports = QLineEdit("common")
        self.banners = QCheckBox("Banner detection")
        self.authorization = QCheckBox(
            "I confirm this target is mine or I have explicit permission to assess it."
        )
        self.authorization.setObjectName("authorizationCheck")

        self.start = QPushButton("START OPERATION")
        self.start.setObjectName("primary")
        self.start.clicked.connect(self.begin_scan)

        grid.addWidget(self.target, 1, 0)
        grid.addWidget(self.profile, 1, 1)
        grid.addWidget(self.ports, 1, 2)
        grid.addWidget(self.banners, 1, 3)
        grid.addWidget(self.authorization, 2, 0, 1, 3)
        grid.addWidget(self.start, 2, 3)

        self.profile_description = QLabel()
        self.profile_description.setObjectName("muted")
        grid.addWidget(self.profile_description, 3, 0, 1, 4)
        root.addWidget(controls)

        status_row = QHBoxLayout()
        self.operation_label = QLabel("OPERATION: NOT STARTED")
        self.operation_label.setObjectName("muted")
        self.stage_label = QLabel("STAGE: READY")
        self.stage_label.setObjectName("muted")
        status_row.addWidget(self.operation_label)
        status_row.addStretch(1)
        status_row.addWidget(self.stage_label)
        root.addLayout(status_row)

        self.progress = QProgressBar()
        self.progress.setValue(0)
        root.addWidget(self.progress)

        body = QHBoxLayout()
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["PORT", "STATE", "SERVICE", "LATENCY", "BANNER"]
        )
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setAlternatingRowColors(True)
        body.addWidget(self.table, 3)

        right = QFrame()
        right.setObjectName("panel")
        right_layout = QVBoxLayout(right)
        right_layout.addWidget(QLabel("LIVE OPERATION TIMELINE"))
        self.events = QTextEdit()
        self.events.setReadOnly(True)
        right_layout.addWidget(self.events)
        right_layout.addWidget(QLabel("BLACKTERM ANALYSIS"))
        self.analysis = QTextEdit()
        self.analysis.setReadOnly(True)
        right_layout.addWidget(self.analysis)
        body.addWidget(right, 2)
        root.addLayout(body, 1)

        self.apply_profile()

    def selected_profile_key(self) -> str:
        return str(self.profile.currentData() or "custom")

    def apply_profile(self):
        profile = get_profile(self.selected_profile_key())
        self.profile_description.setText(profile.description)
        is_custom = profile.key == "custom"
        self.ports.setEnabled(is_custom)
        self.banners.setEnabled(is_custom)
        if not is_custom:
            self.ports.setText(profile.ports)
            self.banners.setChecked(profile.banners)

    def begin_scan(self):
        if not self.authorization.isChecked():
            QMessageBox.warning(
                self,
                "Authorization required",
                "Confirm that you own the target or have explicit permission before starting.",
            )
            return

        target = self.target.text().strip()
        if not target:
            QMessageBox.warning(self, "Target required", "Enter an authorized target first.")
            return

        profile = get_profile(self.selected_profile_key())
        try:
            ports = parse_ports(self.ports.text())
        except Exception as exc:
            QMessageBox.critical(self, "Invalid ports", str(exc))
            return

        if profile.key != "custom":
            self.engine.config.timeout = profile.timeout
            self.engine.config.workers = profile.workers
            self.engine.config.banners = profile.banners
        else:
            self.engine.config.banners = self.banners.isChecked()

        self.start.setEnabled(False)
        self.profile.setEnabled(False)
        self.table.setRowCount(0)
        self.events.clear()
        self.analysis.clear()
        self.progress.setMaximum(len(ports))
        self.progress.setValue(0)
        self.operation_label.setText("OPERATION: INITIALIZING")
        self.stage_label.setText("STAGE: TARGET VALIDATION")
        self.events.append(f"[SCOPE] Authorization confirmed by operator")
        self.events.append(f"[TARGET] {target}")
        self.events.append(f"[PROFILE] {profile.name}")
        self.events.append(f"[PORTS] {len(ports)} TCP ports queued")
        self.events.append(f"[ENGINE] {self.engine.config.workers} workers / {self.engine.config.timeout}s timeout")
        self.events.append("[STAGE 1/4] Target validation and resolution")
        self.scan_started.emit(target)

        self.thread = QThread(self)
        self.worker = ScanWorker(self.engine, target, ports, profile=profile.key)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(self.on_progress)
        self.worker.completed.connect(self.on_complete)
        self.worker.failed.connect(self.on_error)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.finished.connect(self._reset_controls)
        self.thread.start()

    def _reset_controls(self):
        self.start.setEnabled(True)
        self.profile.setEnabled(True)
        self.apply_profile()

    def on_progress(self, done, total, item):
        if done == 1:
            self.stage_label.setText("STAGE: TCP DISCOVERY")
            self.events.append("[STAGE 2/4] TCP discovery running")
        self.progress.setMaximum(total)
        self.progress.setValue(done)
        if item.state == "open":
            row = self.table.rowCount()
            self.table.insertRow(row)
            values = [
                f"{item.port}/tcp",
                item.state,
                item.service,
                f"{item.latency_ms} ms",
                item.banner or "",
            ]
            for col, value in enumerate(values):
                self.table.setItem(row, col, QTableWidgetItem(str(value)))
            self.events.append(f"[OPEN] {item.port}/tcp  {item.service}  {item.latency_ms} ms")
            self.scan_port_observed.emit(self.target.text().strip(), item)
        elif done == total or done % max(1, total // 10) == 0:
            self.events.append(f"[PROGRESS] {done}/{total}")

    def on_complete(self, scan_id, result):
        operation_id = result.operation_id or f"SCAN-{scan_id}"
        self.operation_label.setText(f"OPERATION: {operation_id}")
        self.stage_label.setText("STAGE: COMPLETE")
        self.events.append("[STAGE 3/4] Service classification and plugin analysis")
        self.events.append("[STAGE 4/4] Evidence persisted and summary generated")
        self.events.append(
            f"[DONE] {operation_id} completed in {result.duration_seconds}s with "
            f"{len(result.open_ports)} open port(s)."
        )
        self.events.append(f"[RECORD] Local scan record #{scan_id}")
        self.events.append(f"[PROFILE] Hostname: {result.hostname or 'Unknown'}")
        self.events.append(f"[PROFILE] Average open latency: {result.average_open_latency} ms")
        summary = "\n\n".join(build_summary(result))
        surface = build_attack_surface(result)
        self.analysis.setPlainText(
            f"OPERATION\n{operation_id}\n\n"
            f"PROFILE\n{result.profile.upper()}\n\n"
            f"{summary}\n\n"
            f"TARGET PROFILE\nHostname: {result.hostname or 'Unknown'}\n"
            f"Average open latency: {result.average_open_latency} ms\n\n"
            f"ATTACK SURFACE\nRisk: {surface.risk_level} ({surface.risk_score}/100)\n"
            f"Health score: {surface.attack_surface_score}/100\n"
            f"Findings: {len(surface.findings)}"
        )
        self.table.resizeColumnsToContents()
        self.scan_completed.emit(scan_id, result)

    def on_error(self, message):
        self.operation_label.setText("OPERATION: FAILED")
        self.stage_label.setText("STAGE: ERROR")
        self.events.append(f"[ERROR] {message}")
        QMessageBox.critical(self, "Scan failed", message)
