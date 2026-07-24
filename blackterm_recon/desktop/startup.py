from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QTimer, Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
)


class StartupSequence(QDialog):
    accepted_operator = Signal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("BLACKTERM")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(860, 540)

        shell = QFrame()
        shell.setObjectName("panel")
        shell.setStyleSheet(
            """
            QFrame#panel { background: #050914; border: 1px solid #285273; border-radius: 18px; }
            QLabel { color: #f5efff; }
            QLineEdit { background: #07111f; color: #f5efff; border: 1px solid #285273; border-radius: 8px; padding: 10px; }
            QPushButton { background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #31b7ff,stop:1 #36e6b0); color: #04111c; font-weight: 900; border: none; border-radius: 8px; padding: 11px; }
            QProgressBar { background: #07111f; border: 1px solid #285273; border-radius: 6px; text-align: center; }
            QProgressBar::chunk { background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #31b7ff,stop:0.65 #27c6ee,stop:1 #b000ff); border-radius: 5px; }
            """
        )
        outer = QVBoxLayout(self)
        outer.addWidget(shell)
        self.stack = QStackedLayout(shell)

        boot = QWidget()
        boot_layout = QVBoxLayout(boot)
        boot_layout.setContentsMargins(54, 44, 54, 44)
        title = QLabel("BLACKTERM")
        title.setStyleSheet("font-size: 48px; font-weight: 950; color: #31b7ff; letter-spacing: 3px;")
        sub = QLabel("INTELLIGENCE OPERATING SYSTEM // BLACKTERM X")
        sub.setStyleSheet("font-size: 15px; color: #9b8aa8;")
        self.current_module = QLabel("BOOTSTRAP")
        self.current_module.setStyleSheet("font-size:18px;font-weight:900;color:#31b7ff;")
        self.boot_log = QLabel()
        self.boot_log.setStyleSheet("font-family: Consolas; font-size: 13px;")
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setFormat("INITIALIZING %p%")
        boot_layout.addWidget(title)
        boot_layout.addWidget(sub)
        boot_layout.addSpacing(24)
        boot_layout.addWidget(self.current_module)
        boot_layout.addWidget(self.boot_log, 1)
        boot_layout.addWidget(self.progress)
        self.stack.addWidget(boot)

        login = QWidget()
        login_layout = QVBoxLayout(login)
        login_layout.setContentsMargins(80, 62, 80, 62)
        login_title = QLabel("OPERATOR ACCESS")
        login_title.setStyleSheet("font-size: 28px; font-weight: 900; color: #31b7ff;")
        login_sub = QLabel("Local profile only. No remote authentication is performed.")
        login_sub.setStyleSheet("color: #9b8aa8;")
        self.operator = QLineEdit("TYLER")
        self.operator.setPlaceholderText("Operator name")
        self.clearance = QLabel("CLEARANCE // LEVEL 3\nSESSION // AUTHORIZED\nCORE // ONLINE")
        self.clearance.setStyleSheet("font-family: Consolas; font-size: 14px;")
        enter = QPushButton("ENTER PLATFORM")
        enter.clicked.connect(self.accept_login)
        login_layout.addWidget(login_title)
        login_layout.addWidget(login_sub)
        login_layout.addSpacing(30)
        login_layout.addWidget(QLabel("OPERATOR"))
        login_layout.addWidget(self.operator)
        login_layout.addSpacing(16)
        login_layout.addWidget(self.clearance)
        login_layout.addStretch()
        login_layout.addWidget(enter)
        self.stack.addWidget(login)

        self.steps = [
            ("CORE", "Kernel services initialized"),
            ("VAULT", "Opening encrypted evidence workspace"),
            ("EVENT BUS", "Persistent investigation stream online"),
            ("RECON", "Reconnaissance engines armed"),
            ("INTELLIGENCE", "OSINT and threat context synchronized"),
            ("AI ANALYST", "BLACKTERM analyst context loaded"),
            ("GRAPH ENGINE", "Relationship renderer and signal layer online"),
            ("PLUGINS", "Extension registry verified"),
            ("MISSION CONTROL", "Operator environment prepared"),
            ("READY", "BLACKTERM X is ready"),
        ]
        self.step_index = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.advance)
        self.timer.start(185)

    def advance(self):
        if self.step_index < len(self.steps):
            module, line = self.steps[self.step_index]
            self.current_module.setText(module)
            existing = self.boot_log.text()
            self.boot_log.setText(existing + f"[OK] {line}\n")
            self.progress.setValue(int((self.step_index + 1) / len(self.steps) * 100))
            self.step_index += 1
            return
        self.timer.stop()
        self._fade_to_login()

    def _fade_to_login(self):
        animation = QPropertyAnimation(self, b"windowOpacity", self)
        animation.setDuration(180)
        animation.setStartValue(1.0)
        animation.setEndValue(0.2)
        animation.setEasingCurve(QEasingCurve.InOutCubic)
        animation.finished.connect(self._show_login)
        animation.start()
        self._fade_out = animation

    def _show_login(self):
        self.stack.setCurrentIndex(1)
        animation = QPropertyAnimation(self, b"windowOpacity", self)
        animation.setDuration(220)
        animation.setStartValue(0.2)
        animation.setEndValue(1.0)
        animation.setEasingCurve(QEasingCurve.OutCubic)
        animation.start()
        self._fade_in = animation

    def accept_login(self):
        name = self.operator.text().strip() or "OPERATOR"
        self.accepted_operator.emit(name)
        self.accept()
