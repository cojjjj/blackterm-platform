from __future__ import annotations

import os

import psutil
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QListWidget,
    QVBoxLayout, QWidget
)

from ..widgets import MetricCard, PulseDot, Sparkline


class DashboardPage(QWidget):
    def __init__(self, engine, operator="OPERATOR"):
        super().__init__()
        self.engine = engine
        self.operator = operator
        root = QVBoxLayout(self)

        title_row = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("Operations Dashboard")
        title.setObjectName("pageTitle")
        self.subtitle = QLabel()
        self.subtitle.setObjectName("muted")
        title_box.addWidget(title)
        title_box.addWidget(self.subtitle)
        title_row.addLayout(title_box)
        title_row.addStretch()
        title_row.addWidget(PulseDot())
        ready = QLabel("ENGINE READY")
        ready.setObjectName("statusActive")
        title_row.addWidget(ready)
        root.addLayout(title_row)

        cards = QHBoxLayout()
        self.scans = MetricCard("Saved Scans", "0", "Persistent SQLite history")
        self.ports = MetricCard("Open Ports", "0", "Across saved scans")
        self.cpu = MetricCard("CPU", "0%", "Live local system usage")
        self.memory = MetricCard("Memory", "0%", "Live local system usage")
        for card in (self.scans, self.ports, self.cpu, self.memory):
            cards.addWidget(card)
        root.addLayout(cards)

        body = QGridLayout()
        activity_panel = QFrame()
        activity_panel.setObjectName("panel")
        activity_layout = QVBoxLayout(activity_panel)
        activity_layout.addWidget(QLabel("RECENT ACTIVITY"))
        self.activity = QListWidget()
        activity_layout.addWidget(self.activity)

        trend_panel = QFrame()
        trend_panel.setObjectName("panel")
        trend_layout = QVBoxLayout(trend_panel)
        trend_layout.addWidget(QLabel("OPEN-PORT ACTIVITY"))
        self.sparkline = Sparkline()
        trend_layout.addWidget(self.sparkline)

        engine_panel = QFrame()
        engine_panel.setObjectName("panel")
        engine_layout = QVBoxLayout(engine_panel)
        engine_layout.addWidget(QLabel("ENGINE PROFILE"))
        self.profile = QLabel()
        self.profile.setWordWrap(True)
        self.profile.setObjectName("muted")
        engine_layout.addWidget(self.profile)
        engine_layout.addStretch()

        body.addWidget(activity_panel, 0, 0, 2, 2)
        body.addWidget(trend_panel, 0, 2)
        body.addWidget(engine_panel, 1, 2)
        root.addLayout(body, 1)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_system)
        self.timer.start(1200)
        self.refresh()

    def set_operator(self, operator):
        self.operator = operator
        self.refresh()

    def refresh_system(self):
        self.cpu.set_value(f"{psutil.cpu_percent():.0f}%")
        self.memory.set_value(f"{psutil.virtual_memory().percent:.0f}%")

    def refresh(self):
        stats = self.engine.repository.stats()
        rows = self.engine.repository.list_recent(10)
        self.subtitle.setText(
            f"Welcome, {self.operator}. Authorized local security workspace is online."
        )
        self.scans.set_value(stats["scans"], "Persistent SQLite history")
        self.ports.set_value(stats["open_ports"], "Across saved scans")
        self.refresh_system()

        self.activity.clear()
        for row in rows[:8]:
            self.activity.addItem(
                f"Scan #{row['id']}  {row['target']}  •  {row['open_ports']} open"
            )
        if not rows:
            self.activity.addItem("No scans recorded yet.")

        self.sparkline.set_values(
            list(reversed([int(row["open_ports"]) for row in rows])) or [0]
        )
        process = psutil.Process(os.getpid())
        latest = self.engine.repository.get(rows[0]["id"]) if rows else None
        latest_host = (
            f"\n\nLATEST HOST\n"
            f"{latest.hostname or latest.ip}\n"
            f"{len(latest.open_ports)} open port(s)\n"
            f"Average latency: {latest.average_open_latency} ms"
            if latest else "\n\nLATEST HOST\nNone"
        )
        self.profile.setText(
            f"Workers: {self.engine.config.workers}\n"
            f"Timeout: {self.engine.config.timeout}s\n"
            f"Banner detection: {'Enabled' if self.engine.config.banners else 'Disabled'}\n"
            f"Loaded plugins: {len(self.engine.plugins.plugins)}\n"
            f"Process memory: {process.memory_info().rss / 1024 / 1024:.1f} MB\n"
            f"Database: {self.engine.config.database_path}\n"
            f"Last scan: {stats['last_scan']}" + latest_host
        )
