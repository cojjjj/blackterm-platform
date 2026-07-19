from __future__ import annotations

import math
import random

from PySide6.QtCore import QPointF, QTimer, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPen, QRadialGradient
from PySide6.QtWidgets import QWidget


class AmbientBackdrop(QWidget):
    """Low-cost ambient grid and glow layer that never intercepts input."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.phase = 0.0
        self.points = [
            (
                random.random(),
                random.random(),
                random.uniform(0.35, 1.0),
                random.uniform(0.3, 1.1),
            )
            for _ in range(26)
        ]
        self.timer = QTimer(self)
        self.timer.setInterval(50)
        self.timer.timeout.connect(self.advance)
        self.timer.start()

    def advance(self):
        self.phase = (self.phase + 0.012) % (math.pi * 2)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect()

        # Deep directional wash.
        wash = QLinearGradient(rect.topLeft(), rect.bottomRight())
        wash.setColorAt(0.0, QColor(4, 11, 20, 110))
        wash.setColorAt(0.55, QColor(8, 7, 18, 85))
        wash.setColorAt(1.0, QColor(12, 5, 22, 105))
        painter.fillRect(rect, wash)

        # Slowly breathing cyan and purple glows.
        cyan_x = rect.width() * (0.73 + 0.03 * math.sin(self.phase))
        cyan_y = rect.height() * (0.20 + 0.02 * math.cos(self.phase))
        cyan = QRadialGradient(QPointF(cyan_x, cyan_y), max(rect.width(), rect.height()) * 0.36)
        cyan.setColorAt(0.0, QColor(22, 155, 220, 34))
        cyan.setColorAt(1.0, QColor(22, 155, 220, 0))
        painter.fillRect(rect, cyan)

        purple_x = rect.width() * (0.47 + 0.025 * math.cos(self.phase * 0.8))
        purple_y = rect.height() * (0.88 + 0.02 * math.sin(self.phase))
        purple = QRadialGradient(QPointF(purple_x, purple_y), max(rect.width(), rect.height()) * 0.40)
        purple.setColorAt(0.0, QColor(151, 0, 255, 26))
        purple.setColorAt(1.0, QColor(151, 0, 255, 0))
        painter.fillRect(rect, purple)

        # Subtle grid.
        painter.setPen(QPen(QColor(48, 94, 132, 13), 1))
        grid = 42
        for x in range(0, rect.width(), grid):
            painter.drawLine(x, 0, x, rect.height())
        for y in range(0, rect.height(), grid):
            painter.drawLine(0, y, rect.width(), y)

        # Very faint drifting points.
        painter.setPen(Qt.NoPen)
        for base_x, base_y, speed, size in self.points:
            x = (base_x * rect.width() + self.phase * 18 * speed) % max(1, rect.width())
            y = base_y * rect.height() + math.sin(self.phase * speed + base_x * 8) * 8
            painter.setBrush(QColor(84, 180, 235, 22))
            painter.drawEllipse(QPointF(x, y), size, size)
