from __future__ import annotations

from html import escape

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTextBrowser, QVBoxLayout, QWidget
)

from ..assistant_engine import answer_question


class AIAnalystDock(QFrame):
    close_requested = Signal()
    page_requested = Signal(str)

    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.setObjectName("aiAnalystDock")
        self.setMinimumWidth(360)
        self.setMaximumWidth(430)

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("BLACKTERM AI // ANALYST")
        title.setObjectName("aiDockTitle")
        close = QPushButton("×")
        close.setObjectName("aiDockClose")
        close.setFixedSize(30, 30)
        close.clicked.connect(self.close_requested.emit)
        header.addWidget(title)
        header.addStretch()
        header.addWidget(close)
        root.addLayout(header)

        status = QLabel("● CONTEXT ENGINE ONLINE")
        status.setObjectName("aiDockStatus")
        root.addWidget(status)

        self.chat = QTextBrowser()
        self.chat.setObjectName("aiDockChat")
        self.chat.setOpenExternalLinks(False)
        root.addWidget(self.chat, 1)

        shortcuts = QHBoxLayout()
        for text, prompt in (
            ("SUMMARIZE", "summarize the latest scan"),
            ("RISKS", "what stands out"),
            ("NEXT STEPS", "recommend safe next steps"),
        ):
            button = QPushButton(text)
            button.setObjectName("aiQuickAction")
            button.clicked.connect(lambda _=False, p=prompt: self.ask_text(p))
            shortcuts.addWidget(button)
        root.addLayout(shortcuts)

        row = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText("Ask about the current investigation…")
        self.input.returnPressed.connect(self.ask)
        send = QPushButton("ASK")
        send.setObjectName("primary")
        send.clicked.connect(self.ask)
        row.addWidget(self.input, 1)
        row.addWidget(send)
        root.addLayout(row)

        self._welcome()

    def _welcome(self):
        self.chat.setHtml(
            '<div style="color:#a82be2;font-weight:900;font-size:16px;">ANALYST READY</div>'
            '<div style="color:#9fb0c5;margin-top:8px;line-height:1.5;">'
            'I can summarize saved scans, identify notable exposure, explain services, '
            'and recommend defensive next steps.</div>'
        )

    def latest_result(self):
        try:
            rows = self.engine.repository.list_recent(1)
            return self.engine.repository.get(rows[0]["id"]) if rows else None
        except Exception:
            return None

    def ask(self):
        question = self.input.text().strip()
        if question:
            self.input.clear()
            self.ask_text(question)

    def ask_text(self, question: str):
        result = self.latest_result()
        reply = answer_question(question, result)
        self.chat.append(
            f'<div style="margin:10px 0;color:#31b7ff;font-weight:800;">YOU // {escape(question)}</div>'
            f'<div style="margin:0 0 14px;padding:12px;border:1px solid #7136a8;'
            f'border-radius:10px;background:#0b0d17;color:#f5efff;line-height:1.45;">'
            f'<b style="color:#c25cff;">{escape(reply.title)}</b><br><br>'
            f'{escape(reply.body).replace(chr(10), "<br>")}</div>'
        )
        if getattr(self.engine, "event_bus", None):
            try:
                from ..events import EventLevel
                self.engine.event_bus.emit(
                    "ai", reply.body, title=reply.title,
                    level=EventLevel.AI, module="assistant",
                )
            except Exception:
                pass
