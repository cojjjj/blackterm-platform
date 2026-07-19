from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QObject, QTimer, Qt, Signal
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from .animations import WidgetAnimator


class FadeController(QObject):
    """Compatibility wrapper around the centralized WidgetAnimator."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.animator = WidgetAnimator(self)

    def fade_in(self, widget: QWidget, duration: int = 220):
        return self.animator.fade_in(widget, duration=duration)


class PulseController(QObject):
    """Compatibility wrapper around centralized safe widget pulse animation."""

    def __init__(self, widget: QWidget, minimum: float = 0.72, maximum: float = 1.0):
        super().__init__(widget)
        self.animator = WidgetAnimator(self)
        self.animation = self.animator.pulse(
            widget,
            minimum=minimum,
            maximum=maximum,
            duration=1700,
        )


@dataclass(frozen=True, slots=True)
class BootStage:
    label: str
    progress: int


BOOT_STAGES = (
    BootStage("Loading platform modules", 18),
    BootStage("Connecting Event Bus", 34),
    BootStage("Loading Intelligence Engine", 52),
    BootStage("Loading Investigation Graph", 68),
    BootStage("Loading AI Analyst", 82),
    BootStage("Restoring operator workspace", 94),
    BootStage("Platform ready", 100),
)


class BootOverlay(QFrame):
    completed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("bootOverlay")
        self.setStyleSheet(
            """
            QFrame#bootOverlay {
                background: rgba(5, 8, 15, 248);
                border: 1px solid #214568;
                border-radius: 14px;
            }
            """
        )
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.stage_index = -1

        root = QVBoxLayout(self)
        root.setContentsMargins(48, 40, 48, 40)
        root.addStretch()

        self.brand = QLabel("BLACKTERM")
        self.brand.setAlignment(Qt.AlignCenter)
        self.brand.setStyleSheet(
            "font-size:38px;font-weight:900;color:#ffffff;letter-spacing:4px;"
        )
        self.subtitle = QLabel("INTELLIGENCE PLATFORM")
        self.subtitle.setAlignment(Qt.AlignCenter)
        self.subtitle.setStyleSheet(
            "font-size:10px;font-weight:900;color:#31b7ff;letter-spacing:4px;"
        )
        self.stage = QLabel("INITIALIZING")
        self.stage.setAlignment(Qt.AlignCenter)
        self.stage.setStyleSheet(
            "font-family:Consolas;font-size:12px;color:#b7c7db;margin-top:24px;"
        )
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(True)
        self.progress.setFormat("%p%")
        self.progress.setMinimumHeight(18)

        root.addWidget(self.brand)
        root.addWidget(self.subtitle)
        root.addSpacing(28)
        root.addWidget(self.stage)
        root.addSpacing(10)
        root.addWidget(self.progress)
        root.addStretch()

        self.timer = QTimer(self)
        self.timer.setInterval(230)
        self.timer.timeout.connect(self._advance)

    def start(self):
        self.stage_index = -1
        self.progress.setValue(0)
        self.show()
        self.raise_()
        self.timer.start()

    def _advance(self):
        self.stage_index += 1
        if self.stage_index >= len(BOOT_STAGES):
            self.timer.stop()
            QTimer.singleShot(280, self._finish)
            return
        stage = BOOT_STAGES[self.stage_index]
        self.stage.setText(stage.label.upper() + "...")
        self.progress.setValue(stage.progress)

    def _finish(self):
        self.stage.setText("PLATFORM READY")
        self.progress.setValue(100)
        QTimer.singleShot(180, self._hide_complete)

    def _hide_complete(self):
        self.hide()
        self.completed.emit()


class LoadingStrip(QFrame):
    completed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("loadingStrip")
        self.setStyleSheet(
            """
            QFrame#loadingStrip {
                background:#0b1625;
                border:1px solid #2b5c86;
                border-radius:10px;
            }
            """
        )
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        self.label = QLabel("LOADING INVESTIGATION")
        self.label.setStyleSheet(
            "font-family:Consolas;font-size:10px;font-weight:800;color:#31b7ff;"
        )
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setTextVisible(False)
        layout.addWidget(self.label)
        layout.addWidget(self.progress, 1)
        self.hide()

    def play(self, label: str = "Loading investigation", duration_ms: int = 650):
        self.label.setText(label.upper())
        self.show()
        QTimer.singleShot(max(250, duration_ms), self._finish)

    def _finish(self):
        self.hide()
        self.completed.emit()
