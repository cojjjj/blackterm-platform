from __future__ import annotations

import shlex

from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QLineEdit, QPushButton, QTextEdit,
    QVBoxLayout, QWidget
)

from ...ports import parse_ports
from ...summary import build_summary


class TerminalPage(QWidget):
    def __init__(self, engine, navigate):
        super().__init__()
        self.engine = engine
        self.navigate = navigate
        root = QVBoxLayout(self)
        title = QLabel("BLACKTERM Terminal")
        title.setObjectName("pageTitle")
        sub = QLabel("A controlled command console for local BLACKTERM workflows.")
        sub.setObjectName("muted")
        root.addWidget(title)
        root.addWidget(sub)

        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setStyleSheet("font-family: Consolas; font-size: 13px; padding: 12px;")
        self.output.setPlainText(
            "BLACKTERM TERMINAL v4.0\n"
            "Type 'help' for available commands.\n\n"
        )
        root.addWidget(self.output, 1)

        row = QHBoxLayout()
        prompt = QLabel(">")
        prompt.setStyleSheet("font-size: 22px; font-weight: 900; color: #c000ff;")
        self.input = QLineEdit()
        self.input.setPlaceholderText("help")
        run = QPushButton("RUN")
        run.setObjectName("primary")
        run.clicked.connect(self.execute)
        self.input.returnPressed.connect(self.execute)
        row.addWidget(prompt)
        row.addWidget(self.input, 1)
        row.addWidget(run)
        root.addLayout(row)

    def append(self, text):
        self.output.append(text)

    def execute(self):
        command = self.input.text().strip()
        if not command:
            return
        self.append(f"> {command}")
        self.input.clear()

        try:
            parts = shlex.split(command)
        except ValueError as exc:
            self.append(f"ERROR: {exc}")
            return
        if not parts:
            return

        name = parts[0].lower()
        if name == "help":
            self.append(
                "Commands:\n"
                "  help\n"
                "  clear\n"
                "  history\n"
                "  plugins\n"
                "  config\n"
                "  latest\n"
                "  scan <target> [ports]\n"
                "  open <dashboard|scan|map|cases|reports|assistant>\n"
            )
        elif name == "clear":
            self.output.clear()
        elif name == "history":
            rows = self.engine.repository.list_recent(10)
            for row in rows:
                self.append(
                    f"#{row['id']} {row['target']} {row['ip']} "
                    f"{row['open_ports']} open"
                )
            if not rows:
                self.append("No saved scans.")
        elif name == "plugins":
            plugins = self.engine.plugins.discover()
            if not plugins:
                self.append("No plugins installed.")
            for plugin in plugins:
                self.append(f"{plugin.name} v{plugin.version}")
        elif name == "config":
            for key, value in self.engine.config.to_dict().items():
                self.append(f"{key} = {value}")
        elif name == "latest":
            rows = self.engine.repository.list_recent(1)
            if not rows:
                self.append("No saved scans.")
            else:
                result = self.engine.repository.get(rows[0]["id"])
                self.append("\n".join(build_summary(result)))
        elif name == "scan":
            if len(parts) < 2:
                self.append("Usage: scan <target> [ports]")
                return
            target = parts[1]
            port_spec = parts[2] if len(parts) > 2 else "common"
            ports = parse_ports(port_spec)
            self.append(
                "For responsive operation, scans launch from the LIVE SCAN page.\n"
                f"Prepared target={target}, ports={port_spec} ({len(ports)} ports)."
            )
            self.navigate("LIVE SCAN")
        elif name == "open":
            mapping = {
                "dashboard": "DASHBOARD",
                "scan": "LIVE SCAN",
                "map": "NETWORK MAP",
                "cases": "CASES",
                "reports": "REPORTS",
                "assistant": "AI ASSISTANT",
            }
            destination = mapping.get(parts[1].lower()) if len(parts) > 1 else None
            if destination:
                self.navigate(destination)
            else:
                self.append("Unknown page.")
        else:
            self.append(f"Unknown command: {name}")
