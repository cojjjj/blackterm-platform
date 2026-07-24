from __future__ import annotations

import os
import socket

import psutil
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QProgressBar, QVBoxLayout


class TelemetryGauge(QFrame):
    """Compact live system gauge used by Mission Control."""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setObjectName("telemetryGauge")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(3)
        row = QGridLayout()
        self.title = QLabel(title)
        self.title.setObjectName("muted")
        self.value = QLabel("0%")
        self.value.setObjectName("statusActive")
        row.addWidget(self.title, 0, 0)
        row.addWidget(self.value, 0, 1)
        layout.addLayout(row)
        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setTextVisible(False)
        self.bar.setMaximumHeight(7)
        layout.addWidget(self.bar)

    def set_value(self, value: float, suffix: str = "%"):
        safe = max(0, min(100, int(round(value))))
        self.bar.setValue(safe)
        self.value.setText(f"{safe}{suffix}")


class SystemTelemetryPanel(QFrame):
    """Live local telemetry with no privileged access requirements."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("panel")
        self._last_net = psutil.net_io_counters()
        self._last_disk = psutil.disk_io_counters()

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 9, 10, 9)
        root.setSpacing(6)
        title = QLabel("LIVE SYSTEM TELEMETRY")
        root.addWidget(title)

        self.host = QLabel(f"{socket.gethostname()}  •  PID {os.getpid()}")
        self.host.setObjectName("muted")
        root.addWidget(self.host)

        grid = QGridLayout()
        grid.setSpacing(6)
        self.cpu = TelemetryGauge("CPU")
        self.memory = TelemetryGauge("MEMORY")
        self.disk = TelemetryGauge("DISK")
        self.network = TelemetryGauge("NETWORK")
        grid.addWidget(self.cpu, 0, 0)
        grid.addWidget(self.memory, 0, 1)
        grid.addWidget(self.disk, 1, 0)
        grid.addWidget(self.network, 1, 1)
        root.addLayout(grid)

        self.detail = QLabel("Threads: —  •  Connections: —")
        self.detail.setObjectName("muted")
        root.addWidget(self.detail)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(1000)
        self.refresh()

    def refresh(self):
        cpu = psutil.cpu_percent(interval=None)
        memory = psutil.virtual_memory().percent
        try:
            disk = psutil.disk_usage(os.path.abspath(os.sep)).percent
        except OSError:
            disk = 0

        current_net = psutil.net_io_counters()
        delta_bytes = max(
            0,
            (current_net.bytes_sent + current_net.bytes_recv)
            - (self._last_net.bytes_sent + self._last_net.bytes_recv),
        )
        self._last_net = current_net
        # Scale 0..25 MB/s into a compact operational percentage.
        network_load = min(100, (delta_bytes / (25 * 1024 * 1024)) * 100)

        self.cpu.set_value(cpu)
        self.memory.set_value(memory)
        self.disk.set_value(disk)
        self.network.set_value(network_load)

        process = psutil.Process()
        try:
            connection_count = len(psutil.net_connections(kind="inet"))
        except (psutil.AccessDenied, OSError):
            connection_count = 0
        self.detail.setText(
            f"Threads: {process.num_threads()}  •  Connections: {connection_count}  •  "
            f"Traffic: {delta_bytes / 1024:.1f} KB/s"
        )
