from __future__ import annotations

from collections.abc import Iterable

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from .living_interface import PulseController


NAV_ICONS = {
    "MISSION CONTROL": "◎",
    "OPERATOR DASHBOARD": "◉",
    "PLATFORM": "◆",
    "DASHBOARD": "⌂",
    "LIVE SCAN": "⌁",
    "ATTACK SURFACE": "◈",
    "INVESTIGATION WORKSPACE": "•",
    "NETWORK MAP": "◉",
    "OSINT": "⌖",
    "THREAT INTELLIGENCE": "◌",
    "TERMINAL": ">_",
    "CASES": "▣",
    "EVENT FEED": "≡",
    "HISTORY": "◷",
    "REPORTS": "▤",
    "AI ASSISTANT": "✦",
    "PLUGINS": "◇",
    "SETTINGS": "⚙",
}

# The order here controls both the visual grouping and the default expanded state.
# Any future page not listed below is placed in PLATFORM automatically, so adding a
# module can never make it disappear from navigation.
NAV_SECTIONS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "OPERATIONS",
        (
            "MISSION CONTROL",
            "OPERATOR DASHBOARD",
            "PLATFORM",
            "DASHBOARD",
            "LIVE SCAN",
        ),
    ),
    (
        "INVESTIGATIONS",
        (
            "INVESTIGATION WORKSPACE",
            "CASES",
            "EVENT FEED",
            "HISTORY",
            "REPORTS",
            "AI ASSISTANT",
        ),
    ),
    (
        "INTELLIGENCE",
        (
            "ATTACK SURFACE",
            "OSINT",
            "THREAT INTELLIGENCE",
        ),
    ),
    (
        "VISUALIZATION",
        (
            "NETWORK MAP",
        ),
    ),
    (
        "PLATFORM",
        (
            "TERMINAL",
            "PLUGINS",
            "SETTINGS",
        ),
    ),
)


class DockButton(QPushButton):
    def __init__(self, label: str, icon_text: str, parent=None):
        super().__init__(parent)
        self.label = label
        self.icon_text = icon_text
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(43)
        self.setText(f"{icon_text}   {label.title()}")
        self.setToolTip(label.title())
        self.setObjectName("navigationButton")
        self.setStyleSheet(
            """
            QPushButton#navigationButton {
                text-align: left;
                padding: 9px 12px 9px 18px;
                border: 1px solid transparent;
                border-radius: 9px;
                background: transparent;
                color: #b7c7db;
                font-size: 11px;
                font-weight: 750;
            }
            QPushButton#navigationButton:hover {
                background: #122941;
                border-color: #2b5f8b;
                color: #ffffff;
            }
            QPushButton#navigationButton:checked {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #31b7ff, stop:0.55 #39c7f4, stop:1 #36e6b0);
                border-color: #46c9ff;
                color: #06111d;
            }
            """
        )


class SectionHeader(QPushButton):
    """Collapsible navigation heading with a compact disclosure indicator."""

    def __init__(self, title: str, expanded: bool = False, parent=None):
        super().__init__(parent)
        self.title = title
        self.setCheckable(True)
        self.setChecked(expanded)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(31)
        self.setObjectName("navigationSectionHeader")
        self.toggled.connect(self._sync_text)
        self._sync_text(expanded)
        self.setStyleSheet(
            """
            QPushButton#navigationSectionHeader {
                text-align: left;
                padding: 7px 8px;
                margin-top: 3px;
                border: none;
                border-bottom: 1px solid rgba(49, 183, 255, 48);
                background: transparent;
                color: #6f849d;
                font-size: 9px;
                font-weight: 900;
                letter-spacing: 1.3px;
            }
            QPushButton#navigationSectionHeader:hover {
                color: #d8efff;
                background: rgba(18, 41, 65, 120);
            }
            QPushButton#navigationSectionHeader:checked {
                color: #31b7ff;
            }
            """
        )

    def _sync_text(self, expanded: bool):
        marker = "▼" if expanded else "▶"
        self.setText(f"{marker}  {self.title}")


class CollapsibleSection(QWidget):
    def __init__(self, title: str, expanded: bool = False, parent=None):
        super().__init__(parent)
        self.header = SectionHeader(title, expanded, self)
        self.content = QWidget(self)
        self.content.setObjectName("navigationSectionContent")
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(0, 2, 0, 2)
        self.content_layout.setSpacing(3)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.header)
        layout.addWidget(self.content)

        self.header.toggled.connect(self.content.setVisible)
        self.content.setVisible(expanded)

    def add_widget(self, widget: QWidget):
        self.content_layout.addWidget(widget)

    def set_expanded(self, expanded: bool):
        self.header.setChecked(expanded)

    def is_expanded(self) -> bool:
        return self.header.isChecked()


class Dock(QFrame):
    """Grouped, collapsible BLACKTERM navigation with persistent page routes."""

    page_requested = Signal(int)

    def __init__(self, pages, callback=None, parent=None):
        super().__init__(parent)
        self.pages = pages
        self.callback = callback
        self.buttons: dict[str, DockButton] = {}
        self.sections: dict[str, CollapsibleSection] = {}
        self.label_to_section: dict[str, str] = {}
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
            QWidget#navigationSectionContent {
                background: transparent;
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
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        holder = QWidget()
        holder_layout = QVBoxLayout(holder)
        holder_layout.setContentsMargins(0, 0, 0, 0)
        holder_layout.setSpacing(2)

        self.group = QButtonGroup(self)
        self.group.setExclusive(True)

        index_by_label = {label: index for index, (label, _) in enumerate(pages)}
        configured_labels = {
            label for _, labels in NAV_SECTIONS for label in labels
        }
        ungrouped = tuple(label for label, _ in pages if label not in configured_labels)

        section_specs = list(NAV_SECTIONS)
        if ungrouped:
            # Unknown future modules stay accessible without requiring a dock refactor.
            title, labels = section_specs[-1]
            section_specs[-1] = (title, labels + ungrouped)

        for section_number, (section_title, labels) in enumerate(section_specs):
            visible_labels = tuple(label for label in labels if label in index_by_label)
            if not visible_labels:
                continue

            # Operations starts open. The other groups remain compact until used.
            section = CollapsibleSection(
                section_title,
                expanded=(section_number == 0),
            )
            self.sections[section_title] = section
            holder_layout.addWidget(section)

            for label in visible_labels:
                index = index_by_label[label]
                button = DockButton(label, NAV_ICONS.get(label, "•"))
                button.clicked.connect(
                    lambda checked=False, page_index=index: self.activate(page_index)
                )
                self.group.addButton(button, index)
                self.buttons[label] = button
                self.label_to_section[label] = section_title
                section.add_widget(button)

        holder_layout.addStretch()
        scroll.setWidget(holder)
        root.addWidget(scroll, 1)

        footer_line = QFrame()
        footer_line.setFrameShape(QFrame.HLine)
        footer_line.setStyleSheet("color:#173a5a;")
        root.addWidget(footer_line)

        footer = QLabel("v8.5 // PREMIUM ONLINE")
        footer.setAlignment(Qt.AlignCenter)
        footer.setStyleSheet(
            "font-family:Consolas;font-size:9px;color:#36e6b0;font-weight:800;"
        )
        root.addWidget(footer)

        if pages:
            first_label = pages[0][0]
            first_button = self.buttons.get(first_label)
            if first_button is not None:
                first_button.setChecked(True)
                self.expand_for_label(first_label)

    def expand_for_label(self, label: str):
        section_title = self.label_to_section.get(label)
        section = self.sections.get(section_title or "")
        if section is not None:
            section.set_expanded(True)

    def activate(self, index: int):
        if not 0 <= index < len(self.pages):
            return
        label = self.pages[index][0]
        button = self.buttons.get(label)
        if button is None:
            return
        self.expand_for_label(label)
        button.setChecked(True)
        if self._active_pulse is not None:
            animation = getattr(self._active_pulse, "animation", None)
            if hasattr(animation, "stop"):
                animation.stop()
        self._active_pulse = PulseController(button, 0.86, 1.0)
        self.page_requested.emit(index)
        if callable(self.callback):
            self.callback(index)

    def select_label(self, label: str):
        """Select and reveal a route without re-emitting navigation signals."""
        button = self.buttons.get(label)
        if button is None:
            return
        self.expand_for_label(label)
        button.setChecked(True)

    def set_section_expanded(self, title: str, expanded: bool):
        section = self.sections.get(title.upper())
        if section is not None:
            section.set_expanded(expanded)

    def expanded_sections(self) -> Iterable[str]:
        return (
            title for title, section in self.sections.items() if section.is_expanded()
        )

    def set_compact(self, compact: bool):
        """Optional compatibility helper; labels remain visible by design."""
        self.setMinimumWidth(228)
        self.setMaximumWidth(265)


# v8.2.1+ compatibility alias.
NavigationButton = DockButton
