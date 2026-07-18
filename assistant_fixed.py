from PySide6.QtCore import QTimer
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTextEdit, QVBoxLayout, QWidget
)

from ...summary import build_summary


class AssistantPage(QWidget):
    def __init__(self, engine):
        super().__init__()
        self.engine = engine
        self.pending_text = ""
        self.pending_index = 0

        layout = QVBoxLayout(self)
        title = QLabel("BLACKTERM Assistant")
        title.setObjectName("pageTitle")
        subtitle = QLabel(
            "Grounded analysis based only on saved scan observations."
        )
        subtitle.setObjectName("muted")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        terminal = QFrame()
        terminal.setObjectName("panel")
        terminal_layout = QVBoxLayout(terminal)
        self.chat = QTextEdit()
        self.chat.setReadOnly(True)
        self.chat.setStyleSheet(
            "font-family: Consolas; font-size: 13px; padding: 12px;"
        )
        self.chat.setPlainText(
            "BLACKTERM AI ONLINE\n\n"
            "> Try: what stands out?\n"
            "> Try: recommend safe next steps\n"
            "> Try: summarize the last scan\n"
            "> Try: what services were found?\n"
        )
        terminal_layout.addWidget(self.chat)
        layout.addWidget(terminal, 1)

        row = QHBoxLayout()
        prompt = QLabel(">")
        prompt.setStyleSheet("font-size: 22px; font-weight: 900; color: #c000ff;")
        self.input = QLineEdit()
        self.input.setPlaceholderText("Ask about the latest saved scan...")
        button = QPushButton("ASK")
        button.setObjectName("primary")
        button.clicked.connect(self.ask)
        self.input.returnPressed.connect(self.ask)
        row.addWidget(prompt)
        row.addWidget(self.input, 1)
        row.addWidget(button)
        layout.addLayout(row)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.type_next_character)

    def latest_result(self):
        rows = self.engine.repository.list_recent(1)
        if not rows:
            return None
        return self.engine.repository.get(rows[0]["id"])

    def answer_question(self, question, result):
        lower = question.lower()
        if result is None:
            return "No saved scans exist yet. Run an authorized scan first."

        services = sorted({p.service for p in result.open_ports})
        ports = [p.port for p in result.open_ports]

        if "service" in lower:
            return "Observed services: " + (", ".join(services) or "none")
        if "port" in lower:
            return "Open TCP ports: " + (", ".join(map(str, ports)) or "none")
        if "latency" in lower or "fast" in lower:
            return (
                f"Average latency across observed open ports: "
                f"{result.average_open_latency} ms."
            )
        if "next" in lower or "recommend" in lower:
            actions = []
            if any(s in services for s in {"http", "https", "http-proxy"}):
                actions.append("Review HTTP response headers and TLS configuration.")
            if any(s in services for s in {"microsoft-ds", "netbios-ssn"}):
                actions.append("Confirm Windows file-sharing exposure is intentional.")
            if "ssh" in services:
                actions.append("Confirm SSH access policy and intended network scope.")
            actions.append("Compare this result with an earlier scan for unexpected change.")
            actions.append("Export a report before making configuration changes.")
            return "\n".join(f"• {action}" for action in actions)
        if "platform" in lower or "os" in lower:
            if any(s in services for s in {"microsoft-ds", "epmap", "netbios-ssn"}):
                return (
                    "Observed services are consistent with a Windows host, but "
                    "service exposure alone is not definitive OS identification."
                )
            return "The selected observations are insufficient for a reliable OS conclusion."
        if "stand" in lower:
            return "\n".join(build_summary(result))
        return "\n".join(build_summary(result))

    def ask(self):
        question = self.input.text().strip()
        if not question:
            return
        self.chat.append(f"\nYOU > {question}\nBLACKTERM > ")
        self.pending_text = self.answer_question(question, self.latest_result())
        self.pending_index = 0
        self.input.clear()
        self.timer.start(12)

    def type_next_character(self):
        if self.pending_index >= len(self.pending_text):
            self.timer.stop()
            self.chat.append("\n")
            return
        cursor = self.chat.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(self.pending_text[self.pending_index])
        self.chat.setTextCursor(cursor)
        self.chat.ensureCursorVisible()
        self.pending_index += 1
