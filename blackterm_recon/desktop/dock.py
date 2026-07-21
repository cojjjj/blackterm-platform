from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from .living_interface import PulseController
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


NAV_ICONS = {
    "MISSION CONTROL": "◎",
    "OPERATOR DASHBOARD": "◉",
    "PLATFORM": "◆",
    "DASHBOARD": "⌂",
    "LIVE SCAN": "⌁",
    "ATTACK SURFACE": "◈",
    "NETWORK MAP": "◉",
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
    def __init__(self, label: str, icon_text: str, parent=None):
        super().__init__(parent)
        self.label = label
        self.icon_text = icon_text
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(48)
        self.setText(f"{icon_text}   {label.title()}")
        self.setToolTip(label.title())
        self.setObjectName("navigationButton")
        self.setStyleSheet(
            """
            QPushButton#navigationButton {
                text-align: left;
                padding: 11px 14px;
                border: 1px solid transparent;
                border-radius: 10px;
                background: transparent;
                color: #b7c7db;
                font-size: 12px;
                font-weight: 750;
            }
            QPushButton#navigationButton:hover {
                background: #122941;
                border-color: #2b5f8b;
                color: #ffffff;
            }
            QPushButton#navigationButton:checked {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #31b7ff, stop:0.55 #39c7f4, stop:1 #36e6b0);
                border-color: #46c9ff;
                color: #06111d;
            }
            """
        )


class Dock(QFrame):
    """Readable BLACKTERM navigation with persistent page names."""

    page_requested = Signal(int)

    def __init__(self, pages, callback=None, parent=None):
        super().__init__(parent)
        self.pages = pages
        self.callback = callback
        self.buttons: dict[str, DockButton] = {}
        self._active_pulse = None
        self.setObjectName("navigationDock")
        self.setMinimumWidth(228)
        self.setMaximumWidth(265)
        self.setStyleSheet(
            """
            QFrame#navigationDock {
                background: #080d17;
                border: 1px solid #173a5a;
                border-radius: 12px;
            }
            """
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 12, 10, 12)
        root.setSpacing(8)

        brand = QLabel("BLACKTERM")
        brand.setAlignment(Qt.AlignCenter)
        brand.setStyleSheet(
            "font-size:17px;font-weight:900;color:#f3f8ff;letter-spacing:1.4px;"
        )
        mode = QLabel("INTELLIGENCE PLATFORM")
        mode.setAlignment(Qt.AlignCenter)
        mode.setStyleSheet(
            "font-size:8px;font-weight:800;color:#31b7ff;letter-spacing:1.4px;"
        )
        root.addWidget(brand)
        root.addWidget(mode)

        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setStyleSheet("color:#173a5a;")
        root.addWidget(divider)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        holder = QWidget()
        holder_layout = QVBoxLayout(holder)
        holder_layout.setContentsMargins(0, 0, 0, 0)
        holder_layout.setSpacing(5)

        self.group = QButtonGroup(self)
        self.group.setExclusive(True)

        for index, (label, _) in enumerate(pages):
            button = DockButton(label, NAV_ICONS.get(label, "•"))
            button.clicked.connect(
                lambda checked=False, page_index=index: self.activate(page_index)
            )
            self.group.addButton(button, index)
            self.buttons[label] = button
            holder_layout.addWidget(button)

        holder_layout.addStretch()
        scroll.setWidget(holder)
        root.addWidget(scroll, 1)

        footer = QLabel("v8.5 // PREMIUM ONLINE")
        footer.setAlignment(Qt.AlignCenter)
        footer.setStyleSheet(
            "font-family:Consolas;font-size:9px;color:#36e6b0;font-weight:800;"
        )
        root.addWidget(footer)

        if pages:
            first_label = pages[0][0]
            self.buttons[first_label].setChecked(True)

    def activate(self, index: int):
        if not 0 <= index < len(self.pages):
            return
        label = self.pages[index][0]
        button = self.buttons[label]
        button.setChecked(True)
        if self._active_pulse is not None:
            animation = getattr(self._active_pulse, "animation", None)
            if hasattr(animation, "stop"):
                animation.stop()
        self._active_pulse = PulseController(button, 0.86, 1.0)
        self.page_requested.emit(index)
        if callable(self.callback):
            self.callback(index)

    def set_compact(self, compact: bool):
        """Optional compatibility helper; labels remain visible by design."""
        self.setMinimumWidth(228)
        self.setMaximumWidth(265)


# v8.2.1+ compatibility alias.
NavigationButton = DockButton
