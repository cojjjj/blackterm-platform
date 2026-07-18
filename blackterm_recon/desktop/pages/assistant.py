from __future__ import annotations

from html import escape

from PySide6.QtCore import QTimer
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTextBrowser, QVBoxLayout, QWidget
)

from ...assistant_engine import answer_question


class AssistantPage(QWidget):
    def __init__(self, engine):
        super().__init__()
        self.engine = engine
        self.pending_html = ""
        self.analysis_steps = []
        self.step_index = 0

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

        self.chat = QTextBrowser()
        self.chat.setOpenExternalLinks(False)
        self.chat.setStyleSheet(
            "font-family: Consolas; font-size: 13px; padding: 12px;"
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
        self.timer.timeout.connect(self.advance_analysis)
        self.show_welcome()

    def show_welcome(self):
        self.chat.setHtml(
            """
            <div style="color:#c000ff;font-weight:800;font-size:16px;">BLACKTERM AI ONLINE</div>
            <div style="color:#9b8aa8;margin-top:8px;">
                Try: what stands out?<br>
                Try: recommend safe next steps<br>
                Try: summarize the latest scan<br>
                Try: what services were found?<br>
                Try: explain SMB
            </div>
            """
        )

    def latest_result(self):
        rows = self.engine.repository.list_recent(1)
        if not rows:
            return None
        return self.engine.repository.get(rows[0]["id"])

    def append_card(self, sender: str, body: str, accent: str):
        html = (
            f'<div style="margin:14px 0;padding:12px 14px;'
            f'border:1px solid {accent};border-radius:10px;'
            f'background:#100b17;">'
            f'<div style="color:{accent};font-weight:800;margin-bottom:8px;">'
            f'{escape(sender)}</div>'
            f'<div style="color:#f5efff;white-space:pre-wrap;">'
            f'{escape(body).replace(chr(10), "<br>")}</div>'
            f'</div>'
        )
        cursor = self.chat.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertHtml(html)
        self.chat.setTextCursor(cursor)
        self.chat.ensureCursorVisible()

    def ask(self):
        question = self.input.text().strip()
        if not question:
            return

        self.append_card("YOU", question, "#31b7ff")
        self.input.clear()

        if getattr(self.engine, "event_bus", None):
            from ...events import EventLevel
            self.engine.event_bus.emit(
                "ai", question, title="Assistant Question",
                level=EventLevel.AI, module="assistant",
            )
        reply = answer_question(question, self.latest_result())
        self.pending_reply = reply
        self.analysis_steps = [
            "Reading latest saved scan...",
            "Matching observed ports and services...",
            "Building grounded response...",
        ]
        self.step_index = 0
        self.timer.start(280)

    def advance_analysis(self):
        if self.step_index < len(self.analysis_steps):
            self.append_card(
                "BLACKTERM AI",
                self.analysis_steps[self.step_index],
                "#9b8aa8",
            )
            self.step_index += 1
            return

        self.timer.stop()
        self.append_card(
            f"BLACKTERM AI // {self.pending_reply.title}",
            self.pending_reply.body,
            "#c000ff",
        )
        if getattr(self.engine, "event_bus", None):
            from ...events import EventLevel
            self.engine.event_bus.emit(
                "ai", self.pending_reply.body,
                title=self.pending_reply.title,
                level=EventLevel.AI, module="assistant",
            )
