from __future__ import annotations

from collections.abc import Iterable

from PySide6.QtCore import QEasingCurve, QObject, QPropertyAnimation, QTimer, Signal
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QLabel, QTextEdit


class AnimatedNumberLabel(QLabel):
    """Small reusable integer counter for live platform telemetry."""

    def __init__(self, value: int = 0, parent=None):
        super().__init__(str(int(value)), parent)
        self._value = int(value)
        self._target = int(value)
        self._timer = QTimer(self)
        self._timer.setInterval(18)
        self._timer.timeout.connect(self._step)

    @property
    def value(self) -> int:
        return self._value

    def set_value(self, value: int, *, animate: bool = True):
        self._target = int(value)
        if not animate:
            self._value = self._target
            self.setText(str(self._value))
            return
        if self._value == self._target:
            self.setText(str(self._value))
            return
        if not self._timer.isActive():
            self._timer.start()

    def _step(self):
        distance = self._target - self._value
        if distance == 0:
            self._timer.stop()
            return
        magnitude = max(1, abs(distance) // 7)
        self._value += magnitude if distance > 0 else -magnitude
        if (distance > 0 and self._value > self._target) or (
            distance < 0 and self._value < self._target
        ):
            self._value = self._target
        self.setText(str(self._value))
        if self._value == self._target:
            self._timer.stop()


class TypingTextEdit(QTextEdit):
    typing_finished = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._typing_text = ""
        self._typing_index = 0
        self._typing_chunk = 2
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._type_next)

    def type_text(self, text: str, *, interval_ms: int = 8, chunk_size: int = 2):
        self._timer.stop()
        self._typing_text = text or ""
        self._typing_index = 0
        self._typing_chunk = max(1, int(chunk_size))
        self.clear()
        self._timer.setInterval(max(1, int(interval_ms)))
        if self._typing_text:
            self._timer.start()
        else:
            self.typing_finished.emit()

    def finish_typing(self):
        if not self._timer.isActive():
            return
        self._timer.stop()
        self.setPlainText(self._typing_text)
        self._typing_index = len(self._typing_text)
        self.typing_finished.emit()

    def _type_next(self):
        if not self._typing_text or self._typing_index >= len(self._typing_text):
            self._timer.stop()
            self.typing_finished.emit()
            return
        end = min(len(self._typing_text), self._typing_index + self._typing_chunk)
        self.moveCursor(QTextCursor.MoveOperation.End)
        self.insertPlainText(self._typing_text[self._typing_index:end])
        self._typing_index = end
        self.ensureCursorVisible()
        if self._typing_index >= len(self._typing_text):
            self._timer.stop()
            self.typing_finished.emit()


class StageSequence(QObject):
    """Runs named live-investigation stages in order using one safe Qt timer."""

    stage_started = Signal(str, str, int)
    stage_finished = Signal(str, str, int)
    sequence_finished = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._stages: list[tuple[str, str, int]] = []
        self._index = -1
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._advance)

    def start(self, stages: Iterable[tuple[str, str, int]]):
        self.stop()
        self._stages = [
            (str(key), str(label), max(80, int(duration)))
            for key, label, duration in stages
        ]
        self._index = -1
        self._advance()

    def stop(self):
        self._timer.stop()
        self._stages = []
        self._index = -1

    def _advance(self):
        if 0 <= self._index < len(self._stages):
            key, label, duration = self._stages[self._index]
            self.stage_finished.emit(key, label, self._index)
        self._index += 1
        if self._index >= len(self._stages):
            self.sequence_finished.emit()
            return
        key, label, duration = self._stages[self._index]
        self.stage_started.emit(key, label, self._index)
        self._timer.start(duration)
