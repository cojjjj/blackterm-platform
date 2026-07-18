from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QCheckBox, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QProgressBar, QPushButton, QTableWidget,
    QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget
)

from ...ports import parse_ports
from ...summary import build_summary
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

        title = QLabel("Live Scan")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Run authorized TCP visibility scans without blocking the interface.")
        subtitle.setObjectName("muted")
        root.addWidget(title)
        root.addWidget(subtitle)

        controls = QFrame()
        controls.setObjectName("panel")
        grid = QGridLayout(controls)
        grid.addWidget(QLabel("TARGET"), 0, 0)
        grid.addWidget(QLabel("PORTS"), 0, 1)
        self.target = QLineEdit("127.0.0.1")
        self.ports = QLineEdit("common")
        self.banners = QCheckBox("Banner detection")
        self.banners.setChecked(self.engine.config.banners)
        self.start = QPushButton("START SCAN")
        self.start.setObjectName("primary")
        self.start.clicked.connect(self.begin_scan)
        grid.addWidget(self.target, 1, 0)
        grid.addWidget(self.ports, 1, 1)
        grid.addWidget(self.banners, 1, 2)
        grid.addWidget(self.start, 1, 3)
        root.addWidget(controls)

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
        right_layout.addWidget(QLabel("LIVE EVENT FEED"))
        self.events = QTextEdit()
        self.events.setReadOnly(True)
        right_layout.addWidget(self.events)
        right_layout.addWidget(QLabel("BLACKTERM ANALYSIS"))
        self.analysis = QTextEdit()
        self.analysis.setReadOnly(True)
        right_layout.addWidget(self.analysis)
        body.addWidget(right, 2)
        root.addLayout(body, 1)

    def begin_scan(self):
        try:
            ports = parse_ports(self.ports.text())
        except Exception as exc:
            QMessageBox.critical(self, "Invalid ports", str(exc))
            return

        self.engine.config.banners = self.banners.isChecked()
        self.start.setEnabled(False)
        self.table.setRowCount(0)
        self.events.clear()
        self.analysis.clear()
        self.progress.setMaximum(len(ports))
        self.progress.setValue(0)
        self.events.append(f"[INIT] Target: {self.target.text()}")
        self.events.append(f"[INIT] Selected ports: {len(ports)}")
        self.events.append(f"[ENGINE] Workers: {self.engine.config.workers}")
        self.events.append("[ENGINE] Scan thread started...")
        self.scan_started.emit(self.target.text())

        self.thread = QThread(self)
        self.worker = ScanWorker(self.engine, self.target.text(), ports)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(self.on_progress)
        self.worker.completed.connect(self.on_complete)
        self.worker.failed.connect(self.on_error)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.finished.connect(lambda: self.start.setEnabled(True))
        self.thread.start()

    def on_progress(self, done, total, item):
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
            self.scan_port_observed.emit(self.target.text(), item)
        elif done == total or done % max(1, total // 10) == 0:
            self.events.append(f"Progress: {done}/{total}")

    def on_complete(self, scan_id, result):
        self.events.append(f"[DONE] Scan #{scan_id} completed in {result.duration_seconds}s.")
        self.events.append(f"[PROFILE] Hostname: {result.hostname or 'Unknown'}")
        self.events.append(f"[PROFILE] Average open latency: {result.average_open_latency} ms")
        self.analysis.setPlainText("\n\n".join(build_summary(result)) + f"\n\nTARGET PROFILE\nHostname: {result.hostname or 'Unknown'}\nAverage open latency: {result.average_open_latency} ms")
        self.table.resizeColumnsToContents()
        self.scan_completed.emit(scan_id, result)

    def on_error(self, message):
        self.events.append(f"ERROR: {message}")
        QMessageBox.critical(self, "Scan failed", message)
