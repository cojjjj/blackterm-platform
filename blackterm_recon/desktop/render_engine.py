from __future__ import annotations

import math
import random

from PySide6.QtCore import QPointF, QTimer, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPen, QRadialGradient
from PySide6.QtWidgets import QWidget


class RenderSurface(QWidget):
    """One paint surface for all ambient BLACKTERM visuals."""

    def __init__(self, parent=None, *, particle_count: int = 42):
        super().__init__(parent)
        self.setObjectName("renderSurface")
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAutoFillBackground(False)

        self.phase = 0.0
        rng = random.Random(860)
        self.particles = [
            (
                rng.random(),
                rng.random(),
                rng.uniform(0.10, 0.36),
                rng.uniform(0.4, 1.2),
                rng.uniform(0.7, 1.7),
                rng.randint(14, 34),
            )
            for _ in range(max(0, int(particle_count)))
        ]

        self.timer = QTimer(self)
        self.timer.setTimerType(Qt.TimerType.CoarseTimer)
        self.timer.setInterval(66)
        self.timer.timeout.connect(self.advance)
        self.timer.start()

    def advance(self) -> None:
        if self.isVisible():
            self.phase = (self.phase + 0.018) % (math.pi * 2)
            self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter()
        if not painter.begin(self):
            return

        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            rect = self.rect()
            if rect.isEmpty():
                return

            wash = QLinearGradient(rect.topLeft(), rect.bottomRight())
            wash.setColorAt(0.0, QColor(4, 10, 18, 120))
            wash.setColorAt(0.55, QColor(7, 6, 16, 92))
            wash.setColorAt(1.0, QColor(13, 5, 23, 110))
            painter.fillRect(rect, wash)

            cyan = QRadialGradient(
                QPointF(
                    rect.width() * (0.76 + 0.025 * math.sin(self.phase)),
                    rect.height() * (0.18 + 0.018 * math.cos(self.phase)),
                ),
                max(rect.width(), rect.height()) * 0.36,
            )
            cyan.setColorAt(0.0, QColor(24, 171, 232, 32))
            cyan.setColorAt(1.0, QColor(24, 171, 232, 0))
            painter.fillRect(rect, cyan)

            purple = QRadialGradient(
                QPointF(
                    rect.width() * (0.44 + 0.022 * math.cos(self.phase * 0.8)),
                    rect.height() * (0.86 + 0.018 * math.sin(self.phase)),
                ),
                max(rect.width(), rect.height()) * 0.42,
            )
            purple.setColorAt(0.0, QColor(165, 0, 255, 23))
            purple.setColorAt(1.0, QColor(165, 0, 255, 0))
            painter.fillRect(rect, purple)

            painter.setPen(QPen(QColor(52, 101, 139, 12), 1))
            for x in range(0, rect.width(), 44):
                painter.drawLine(x, 0, x, rect.height())
            for y in range(0, rect.height(), 44):
                painter.drawLine(0, y, rect.width(), y)

            painter.setPen(QPen(QColor(111, 171, 211, 7), 1))
            for y in range(0, rect.height(), 6):
                painter.drawLine(0, y, rect.width(), y)

            painter.setPen(Qt.PenStyle.NoPen)
            width = max(1, rect.width())
            height = max(1, rect.height())
            for base_x, base_y, speed, drift, size, alpha in self.particles:
                x = (base_x * width + self.phase * 34.0 * speed) % width
                y = base_y * height + math.sin(
                    self.phase * drift + base_x * 9.0
                ) * 8.0
                painter.setBrush(QColor(85, 186, 239, alpha))
                painter.drawEllipse(QPointF(x, y), size, size)
        finally:
            painter.end()

    def shutdown(self) -> None:
        self.timer.stop()
