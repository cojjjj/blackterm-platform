from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
)


@dataclass(frozen=True)
class CommandAction:
    command: str
    title: str
    description: str
    keywords: str = ""


DEFAULT_ACTIONS = (
    CommandAction("open mission", "Mission Control", "Launch and monitor investigations", "home operations"),
    CommandAction("open operator", "Operator Dashboard", "Resume active work and review awareness", "dashboard home"),
    CommandAction("open investigation", "Investigation Workspace", "Review evidence, risk, timeline, and notes", "case evidence"),
    CommandAction("open cases", "Cases", "Open saved investigations", "case files"),
    CommandAction("open attack", "Attack Surface", "Review exposure and prioritized findings", "risk services"),
    CommandAction("open graph", "Relationship Graph", "Explore domains, IPs, certificates, and services", "visualization nodes"),
    CommandAction("open global", "Global Intelligence Map", "View geographic intelligence relationships", "world map"),
    CommandAction("open threat", "Threat Intelligence", "Enrich indicators with defensive intelligence", "ioc intel"),
    CommandAction("open osint", "OSINT", "Collect authorized open-source intelligence", "recon"),
    CommandAction("open reports", "Reports", "Generate and review professional reports", "export pdf"),
    CommandAction("open assistant", "BLACKTERM AI", "Summarize findings and suggest next steps", "copilot ai"),
    CommandAction("open plugins", "Plugins", "Manage installed platform extensions", "marketplace modules"),
    CommandAction("open settings", "Settings", "Configure BLACKTERM", "preferences theme"),
)


class CommandPalette(QDialog):
    command_selected = Signal(str)

    def __init__(self, actions=DEFAULT_ACTIONS, parent=None):
        super().__init__(parent)
        self.actions = tuple(actions)
        self.setObjectName("commandPalette")
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setModal(True)
        self.resize(680, 470)

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(10)

        heading = QHBoxLayout()
        title = QLabel("COMMAND PALETTE")
        title.setObjectName("paletteTitle")
        hint = QLabel("ESC to close  •  ENTER to run")
        hint.setObjectName("muted")
        heading.addWidget(title)
        heading.addStretch()
        heading.addWidget(hint)
        root.addLayout(heading)

        self.search = QLineEdit()
        self.search.setObjectName("paletteSearch")
        self.search.setPlaceholderText("Search pages or type a BLACKTERM command…")
        self.search.textChanged.connect(self.refresh)
        self.search.returnPressed.connect(self.run_current)
        root.addWidget(self.search)

        self.results = QListWidget()
        self.results.setObjectName("paletteResults")
        self.results.itemActivated.connect(lambda _item: self.run_current())
        root.addWidget(self.results, 1)
        self.refresh("")

    def showEvent(self, event):
        super().showEvent(event)
        if self.parentWidget():
            frame = self.frameGeometry()
            frame.moveCenter(self.parentWidget().frameGeometry().center())
            self.move(frame.topLeft())
        self.search.clear()
        self.search.setFocus()

    def refresh(self, query: str):
        needle = query.strip().lower()
        self.results.clear()
        ranked = []
        for action in self.actions:
            haystack = f"{action.title} {action.description} {action.command} {action.keywords}".lower()
            if not needle or all(token in haystack for token in needle.split()):
                score = 0 if action.title.lower().startswith(needle) else 1
                ranked.append((score, action.title, action))
        for _, _, action in sorted(ranked):
            item = QListWidgetItem(f"{action.title}\n{action.description}")
            item.setData(Qt.UserRole, action.command)
            item.setToolTip(action.command)
            self.results.addItem(item)
        if self.results.count():
            self.results.setCurrentRow(0)

    def run_current(self):
        item = self.results.currentItem()
        if item is None:
            raw = self.search.text().strip()
            if not raw:
                return
            command = raw
        else:
            command = item.data(Qt.UserRole)
        self.command_selected.emit(str(command))
        self.accept()


class CommandBar(QFrame):
    palette_requested = Signal()

    def __init__(self, execute_callback, parent=None):
        super().__init__(parent)
        self.setObjectName("commandBar")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 7, 12, 7)
        layout.setSpacing(10)

        prompt = QLabel("blackterm>")
        prompt.setObjectName("commandPrompt")
        self.input = QLineEdit()
        self.input.setObjectName("commandInput")
        self.input.setPlaceholderText("Type a command or press Ctrl+K…")
        self.input.returnPressed.connect(self.execute)
        self.execute_callback = execute_callback

        shortcut = QLabel("CTRL K")
        shortcut.setObjectName("shortcutBadge")
        shortcut.setToolTip("Open command palette")
        shortcut.mousePressEvent = lambda _event: self.palette_requested.emit()

        layout.addWidget(prompt)
        layout.addWidget(self.input, 1)
        layout.addWidget(shortcut)

    def execute(self):
        command = self.input.text().strip()
        if command:
            self.execute_callback(command)
            self.input.clear()

    def install_palette_shortcut(self, parent):
        shortcut = QShortcut(QKeySequence("Ctrl+K"), parent)
        shortcut.setContext(Qt.ApplicationShortcut)
        shortcut.activated.connect(self.palette_requested.emit)
        return shortcut
