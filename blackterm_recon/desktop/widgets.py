from __future__ import annotations

import math
import random

from PySide6.QtCore import Property, QEasingCurve, QPointF, QPropertyAnimation, QTimer, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QFrame, QLabel, QGraphicsDropShadowEffect, QVBoxLayout, QWidget


def add_glow(widget: QWidget, color: str = "#c000ff", blur: int = 24, alpha: int = 80):
    effect = QGraphicsDropShadowEffect(widget)
    glow = QColor(color)
    glow.setAlpha(alpha)
    effect.setColor(glow)
    effect.setBlurRadius(blur)
    effect.setOffset(0, 0)
    widget.setGraphicsEffect(effect)


class GlassPanel(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("glassPanel")


class MetricCard(QFrame):
    """Metric card with a small count-up animation for numeric values."""

    def __init__(self, label, value="0", caption=""):
        super().__init__()
        self.setObjectName("metricCard")
        self._display_value = 0
        self._target_value = 0
        self._animation_step = 0
        self._animation_timer = QTimer(self)
        self._animation_timer.setInterval(22)
        self._animation_timer.timeout.connect(self._advance_animation)

        layout = QVBoxLayout(self)
        title = QLabel(label.upper())
        title.setObjectName("muted")
        self.value = QLabel(str(value))
        self.value.setObjectName("metricValue")
        self.caption = QLabel(caption)
        self.caption.setObjectName("muted")
        layout.addWidget(title)
        layout.addWidget(self.value)
        layout.addWidget(self.caption)
        layout.addStretch()
        add_glow(self, blur=18, alpha=35)

        try:
            self._display_value = int(value)
            self._target_value = int(value)
        except (TypeError, ValueError):
            pass

    def set_value(self, value, caption=None):
        if caption is not None:
            self.caption.setText(caption)
        try:
            target = int(value)
        except (TypeError, ValueError):
            self._animation_timer.stop()
            self.value.setText(str(value))
            return

        if target == self._target_value and self.value.text() == str(target):
            return

        self._target_value = target
        distance = abs(self._target_value - self._display_value)
        self._animation_step = max(1, math.ceil(distance / 14))
        self._animation_timer.start()

    def _advance_animation(self):
        if self._display_value < self._target_value:
            self._display_value = min(
                self._target_value, self._display_value + self._animation_step
            )
        elif self._display_value > self._target_value:
            self._display_value = max(
                self._target_value, self._display_value - self._animation_step
            )
        else:
            self._animation_timer.stop()
        self.value.setText(str(self._display_value))
        if self._display_value == self._target_value:
            self._animation_timer.stop()


class PulseDot(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._radius = 4.0
        self.setFixedSize(30, 30)
        self.anim = QPropertyAnimation(self, b"radius", self)
        self.anim.setStartValue(4.0)
        self.anim.setEndValue(11.0)
        self.anim.setDuration(950)
        self.anim.setLoopCount(-1)
        self.anim.setEasingCurve(QEasingCurve.InOutSine)
        self.anim.start()

    def get_radius(self):
        return self._radius

    def set_radius(self, value):
        self._radius = value
        self.update()

    radius = Property(float, get_radius, set_radius)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        center = self.rect().center()
        glow = QColor("#c000ff")
        glow.setAlpha(45)
        painter.setBrush(glow)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(center, int(self._radius), int(self._radius))
        painter.setBrush(QColor("#c000ff"))
        painter.drawEllipse(center, 4, 4)


class Sparkline(QWidget):
    """Interpolates between datasets so activity changes slide smoothly."""

    def __init__(self, values=None, parent=None):
        super().__init__(parent)
        initial = [float(v) for v in (values or [1, 2, 1, 3, 2, 5, 4])]
        self.values = initial
        self._from_values = initial[:]
        self._to_values = initial[:]
        self._frame = 12
        self._frames = 12
        self._timer = QTimer(self)
        self._timer.setInterval(24)
        self._timer.timeout.connect(self._animate)
        self.setMinimumHeight(110)

    def set_values(self, values):
        incoming = [float(v) for v in (values or [0])]
        length = max(len(self.values), len(incoming), 2)
        self._from_values = self._normalize(self.values, length)
        self._to_values = self._normalize(incoming, length)
        self._frame = 0
        self._timer.start()

    @staticmethod
    def _normalize(values, length):
        values = list(values or [0])
        if len(values) >= length:
            return values[-length:]
        return [values[0]] * (length - len(values)) + values

    def _animate(self):
        self._frame += 1
        progress = min(1.0, self._frame / self._frames)
        eased = 1.0 - (1.0 - progress) ** 3
        self.values = [
            start + (end - start) * eased
            for start, end in zip(self._from_values, self._to_values)
        ]
        self.update()
        if progress >= 1.0:
            self.values = self._to_values[:]
            self._timer.stop()

    def paintEvent(self, event):
        if len(self.values) < 2:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        width = max(1, self.width() - 20)
        height = max(1, self.height() - 20)
        low = min(self.values)
        span = max(1.0, max(self.values) - low)
        points = [
            QPointF(
                10 + i * width / (len(self.values) - 1),
                10 + height - (value - low) * height / span,
            )
            for i, value in enumerate(self.values)
        ]

        path = QPainterPath(points[0])
        for point in points[1:]:
            path.lineTo(point)

        gradient = QLinearGradient(0, 0, self.width(), 0)
        gradient.setColorAt(0, QColor("#7f3cff"))
        gradient.setColorAt(1, QColor("#c000ff"))
        painter.setPen(QPen(gradient, 3))
        painter.drawPath(path)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#c000ff"))
        for point in points:
            painter.drawEllipse(point, 3, 3)


class ThreatMeter(QWidget):
    LEVELS = (
        (24, "LOW", "#35df83"),
        (49, "GUARDED", "#ffd166"),
        (74, "ELEVATED", "#ff9f43"),
        (100, "CRITICAL", "#ff5c7a"),
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self._value = 0
        self._target = 0
        self._timer = QTimer(self)
        self._timer.setInterval(24)
        self._timer.timeout.connect(self._tick)
        self.setMinimumHeight(62)

    def set_value(self, value: int):
        self._target = max(0, min(100, int(value)))
        self._timer.start()

    def _tick(self):
        delta = self._target - self._value
        if delta == 0:
            self._timer.stop()
            return
        self._value += max(-5, min(5, delta))
        self.update()

    def level(self):
        for ceiling, label, color in self.LEVELS:
            if self._value <= ceiling:
                return label, QColor(color)
        return "CRITICAL", QColor("#ff5c7a")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        label, color = self.level()
        bar_rect = self.rect().adjusted(8, 30, -8, -12)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#111d2b"))
        painter.drawRoundedRect(bar_rect, 7, 7)
        fill = bar_rect.adjusted(0, 0, -int(bar_rect.width() * (100 - self._value) / 100), 0)
        painter.setBrush(color)
        painter.drawRoundedRect(fill, 7, 7)
        painter.setPen(color)
        painter.drawText(8, 20, f"THREAT LEVEL: {label}   {self._value}%")


class ParticleField(QWidget):
    """A lightweight visual background. It does not intercept mouse input."""

    def __init__(self, parent=None, count=56):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.particles = []
        for _ in range(count):
            self.particles.append(
                [
                    random.random(),
                    random.random(),
                    random.uniform(0.00015, 0.00055),
                    random.uniform(1.0, 2.5),
                ]
            )
        self.mouse = QPointF(-1000, -1000)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(30)

    def set_mouse_position(self, point):
        self.mouse = QPointF(point)
        self.update()

    def tick(self):
        for particle in self.particles:
            particle[1] -= particle[2]
            if particle[1] < -0.02:
                particle[0] = random.random()
                particle[1] = 1.02
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        for x, y, speed, size in self.particles:
            px = x * self.width()
            py = y * self.height()
            distance = math.hypot(px - self.mouse.x(), py - self.mouse.y())
            alpha = 105 if distance < 150 else 38
            color = QColor("#c000ff")
            color.setAlpha(alpha)
            painter.setPen(Qt.NoPen)
            painter.setBrush(color)
            painter.drawEllipse(QPointF(px, py), size, size)

class TypingLabel(QLabel):
    """Streams text into a label without blocking the UI."""

    def __init__(self, text="", parent=None, interval=12):
        super().__init__(parent)
        self._full_text = ""
        self._index = 0
        self._interval = interval
        self._typing_timer = QTimer(self)
        self._typing_timer.timeout.connect(self._type_next)
        self.setWordWrap(True)
        if text:
            self.set_typed_text(text, immediate=True)

    def set_typed_text(self, text: str, immediate: bool = False):
        self._typing_timer.stop()
        self._full_text = str(text)
        if immediate or not self.isVisible():
            self._index = len(self._full_text)
            self.setText(self._full_text)
            return
        self._index = 0
        self.setText("")
        self._typing_timer.start(self._interval)

    def _type_next(self):
        self._index += 1
        self.setText(self._full_text[: self._index] + ("▌" if self._index < len(self._full_text) else ""))
        if self._index >= len(self._full_text):
            self._typing_timer.stop()
            self.setText(self._full_text)
