from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel


class LiveStatusBar(QFrame):
    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.setObjectName("liveStatusBar")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 5, 12, 5)
        layout.setSpacing(18)
        self.labels = []
        for text in ("● RECON READY", "● THREAT FEED CONNECTED", "● AI READY", "● MODULES ONLINE"):
            label = QLabel(text)
            label.setObjectName("liveStatusItem")
            self.labels.append(label)
            layout.addWidget(label)
        layout.addStretch()
        self.clock = QLabel()
        self.clock.setObjectName("liveStatusClock")
        layout.addWidget(self.clock)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(1000)
        self.refresh()

    def refresh(self):
        self.clock.setText(datetime.now().strftime("SYSTEM %H:%M:%S"))
        try:
            scans = self.engine.repository.list_recent(500)
            self.labels[0].setText(f"● RECON READY  //  {len(scans)} SAVED")
        except Exception:
            pass
