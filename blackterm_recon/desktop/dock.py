from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QEvent, QVariantAnimation
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QGraphicsDropShadowEffect,
    QPushButton,
    QVBoxLayout,
)


ICONS = {
    "MISSION CONTROL": "◉",
    "PLATFORM": "◈",
    "DASHBOARD": "⌂",
    "LIVE SCAN": "⌁",
    "NETWORK MAP": "◎",
    "TERMINAL": ">_",
    "CASES": "▣",
    "EVENT FEED": "≡",
    "HISTORY": "◷",
    "REPORTS": "▤",
    "AI ASSISTANT": "✦",
    "PLUGINS": "◇",
    "SETTINGS": "⚙",
}


class DockButton(QPushButton):
    """Dock button with a restrained lift/glow animation."""

    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self._base_height = 54
        self.setFixedHeight(self._base_height)
        self._animation = QVariantAnimation(self)
        self._animation.setDuration(150)
        self._animation.setEasingCurve(QEasingCurve.OutCubic)
        self._animation.valueChanged.connect(self._apply_hover)
        self._glow = QGraphicsDropShadowEffect(self)
        self._glow.setOffset(0, 0)
        self._glow.setColor(QColor(192, 0, 255, 0))
        self._glow.setBlurRadius(0)
        self.setGraphicsEffect(self._glow)

    def enterEvent(self, event):
        self._animate_to(1.0)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._animate_to(0.0)
        super().leaveEvent(event)

    def _animate_to(self, target: float):
        start = float(self._animation.currentValue() or 0.0)
        self._animation.stop()
        self._animation.setStartValue(start)
        self._animation.setEndValue(target)
        self._animation.start()

    def _apply_hover(self, amount):
        amount = float(amount)
        font = self.font()
        font.setPointSizeF(10.0 + amount * 1.6)
        self.setFont(font)
        self._glow.setBlurRadius(amount * 26)
        self._glow.setColor(QColor(192, 0, 255, int(amount * 150)))


class Dock(QFrame):
    def __init__(self, pages, show_page):
        super().__init__()
        self.setObjectName("sidebar")
        self.setFixedWidth(86)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 14, 10, 14)
        layout.setSpacing(8)
        group = QButtonGroup(self)
        group.setExclusive(True)
        self.buttons = {}

        for index, (label, _) in enumerate(pages):
            button = DockButton(ICONS.get(label, "•"))
            button.setToolTip(label)
            button.setObjectName("dockButton")
            button.setCheckable(True)
            button.clicked.connect(
                lambda checked=False, page_index=index: show_page(page_index)
            )
            group.addButton(button)
            layout.addWidget(button)
            self.buttons[label] = button
            if index == 0:
                button.setChecked(True)

        layout.addStretch()
