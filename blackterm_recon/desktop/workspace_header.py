from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout


class WorkspaceHeader(QFrame):
    new_investigation_requested = Signal()
    command_palette_requested = Signal()

    def __init__(self, operator: str, parent=None):
        super().__init__(parent)
        self.setObjectName("workspaceHeader")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 11, 14, 11)
        layout.setSpacing(14)

        identity = QVBoxLayout()
        identity.setSpacing(1)
        self.eyebrow = QLabel("BLACKTERM // RECON")
        self.eyebrow.setObjectName("headerEyebrow")
        self.title = QLabel("Mission Control")
        self.title.setObjectName("headerTitle")
        identity.addWidget(self.eyebrow)
        identity.addWidget(self.title)
        layout.addLayout(identity)
        layout.addStretch()

        self.status = QLabel("● PLATFORM ONLINE")
        self.status.setObjectName("onlineBadge")
        layout.addWidget(self.status)

        self.clock = QLabel()
        self.clock.setObjectName("headerClock")
        self.clock.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.addWidget(self.clock)

        operator_label = QLabel(operator.upper())
        operator_label.setObjectName("operatorBadge")
        layout.addWidget(operator_label)

        command = QPushButton("⌘  COMMAND")
        command.setObjectName("headerCommand")
        command.clicked.connect(self.command_palette_requested.emit)
        layout.addWidget(command)

        new_case = QPushButton("＋ NEW INVESTIGATION")
        new_case.setObjectName("primary")
        new_case.clicked.connect(self.new_investigation_requested.emit)
        layout.addWidget(new_case)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_clock)
        self.timer.start(1000)
        self.update_clock()

    def update_clock(self):
        self.clock.setText(datetime.now().strftime("%H:%M:%S\n%d %b %Y").upper())

    def set_page(self, label: str):
        friendly = {
            "AI ASSISTANT": "BLACKTERM AI",
            "LIVE SCAN": "Authorized Live Scan",
            "GLOBAL INTELLIGENCE MAP": "Global Intelligence",
        }.get(label, label.title())
        self.title.setText(friendly)
