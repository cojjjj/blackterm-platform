from __future__ import annotations

import math
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject, QTimer, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QWidget


class AnimationRegistry(QObject):
    """Own timer animations and stop them cleanly."""

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._timers: list[QTimer] = []

    def keep_timer(self, timer: QTimer) -> QTimer:
        self._timers.append(timer)
        return timer

    def release_timer(self, timer: QTimer) -> None:
        if timer in self._timers:
            self._timers.remove(timer)
        timer.stop()
        timer.deleteLater()

    def stop_all(self) -> None:
        for timer in list(self._timers):
            timer.stop()
            timer.deleteLater()
        self._timers.clear()


class WidgetAnimator(QObject):
    """Paint-safe widget updates without off-screen effect rendering."""

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self.registry = AnimationRegistry(self)
        self._pulses: list[PalettePulse] = []

    def fade_in(
        self,
        widget: QWidget,
        *,
        duration: int = 180,
        start: float = 0.0,
        end: float = 1.0,
    ) -> None:
        widget.show()
        widget.raise_()
        widget.update()

    def pulse(
        self,
        widget: QWidget,
        *,
        minimum: float = 0.76,
        maximum: float = 1.0,
        duration: int = 1700,
    ) -> "PalettePulse":
        pulse = PalettePulse(widget, duration=duration)
        self._pulses.append(pulse)
        pulse.destroyed.connect(lambda: self._release_pulse(pulse))
        pulse.start()
        return pulse

    def _release_pulse(self, pulse: "PalettePulse") -> None:
        if pulse in self._pulses:
            self._pulses.remove(pulse)

    def stop_all(self) -> None:
        for pulse in list(self._pulses):
            pulse.stop()
            pulse.deleteLater()
        self._pulses.clear()
        self.registry.stop_all()


class PalettePulse(QObject):
    """Pulse a widget's foreground palette without widget capture."""

    def __init__(self, widget: QWidget, *, duration: int = 1700):
        super().__init__(widget)
        self.widget = widget
        self.base_palette = widget.palette()
        self.elapsed = 0
        self.duration = max(600, int(duration))

        self.timer = QTimer(self)
        self.timer.setTimerType(Qt.TimerType.CoarseTimer)
        self.timer.setInterval(100)
        self.timer.timeout.connect(self.step)

    def start(self) -> None:
        self.timer.start()

    def stop(self) -> None:
        self.timer.stop()
        try:
            self.widget.setPalette(self.base_palette)
            self.widget.update()
        except RuntimeError:
            pass

    def step(self) -> None:
        self.elapsed = (self.elapsed + self.timer.interval()) % self.duration
        progress = self.elapsed / self.duration
        factor = 0.80 + 0.20 * (
            0.5 + 0.5 * math.sin(progress * math.pi * 2)
        )

        try:
            palette = self.base_palette
            base = self.base_palette.color(self.widget.foregroundRole())
            color = QColor(base)
            color.setRed(min(255, int(color.red() * factor + 14)))
            color.setGreen(min(255, int(color.green() * factor + 14)))
            color.setBlue(min(255, int(color.blue() * factor + 14)))
            palette.setColor(self.widget.foregroundRole(), color)
            self.widget.setPalette(palette)
            self.widget.update()
        except RuntimeError:
            self.timer.stop()


class GraphicsItemAnimator(QObject):
    """Timer-driven opacity and scale for plain graphics items."""

    finished = Signal(object)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self.registry = AnimationRegistry(self)

    def fade(
        self,
        item: Any,
        *,
        start: float = 0.0,
        end: float = 1.0,
        duration: int = 320,
        interval: int = 16,
        on_finished: Callable[[], None] | None = None,
    ) -> QTimer:
        start_value = float(start)
        end_value = float(end)
        duration_ms = max(1, int(duration))
        elapsed = 0

        item.setOpacity(start_value)
        timer = QTimer(self)
        timer.setTimerType(Qt.TimerType.PreciseTimer)
        timer.setInterval(max(8, int(interval)))
        self.registry.keep_timer(timer)

        def step() -> None:
            nonlocal elapsed
            elapsed += timer.interval()
            progress = min(1.0, elapsed / duration_ms)
            eased = 1.0 - (1.0 - progress) ** 3
            value = start_value + (end_value - start_value) * eased

            try:
                item.setOpacity(value)
            except RuntimeError:
                self.registry.release_timer(timer)
                return

            if progress >= 1.0:
                self.registry.release_timer(timer)
                if on_finished:
                    on_finished()
                self.finished.emit(item)

        timer.timeout.connect(step)
        timer.start()
        return timer

    def scale(
        self,
        item: Any,
        *,
        start: float = 0.2,
        end: float = 1.0,
        duration: int = 300,
        interval: int = 16,
    ) -> QTimer:
        start_value = float(start)
        end_value = float(end)
        duration_ms = max(1, int(duration))
        elapsed = 0

        item.setScale(start_value)
        timer = QTimer(self)
        timer.setTimerType(Qt.TimerType.PreciseTimer)
        timer.setInterval(max(8, int(interval)))
        self.registry.keep_timer(timer)

        def step() -> None:
            nonlocal elapsed
            elapsed += timer.interval()
            progress = min(1.0, elapsed / duration_ms)
            c1 = 1.70158
            c3 = c1 + 1
            eased = 1 + c3 * (progress - 1) ** 3 + c1 * (progress - 1) ** 2
            eased = max(0.0, min(1.12, eased))
            value = start_value + (end_value - start_value) * eased

            try:
                item.setScale(value)
            except RuntimeError:
                self.registry.release_timer(timer)
                return

            if progress >= 1.0:
                try:
                    item.setScale(end_value)
                except RuntimeError:
                    pass
                self.registry.release_timer(timer)

        timer.timeout.connect(step)
        timer.start()
        return timer
