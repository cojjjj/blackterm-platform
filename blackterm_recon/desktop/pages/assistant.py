from __future__ import annotations

from html import escape

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QGuiApplication, QTextCursor
from PySide6.QtWidgets import (
    QComboBox, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QProgressBar, QTextBrowser, QVBoxLayout, QWidget,
)

from ...assistant_engine import answer_question, build_analyst_brief


class AssistantPage(QWidget):
    def __init__(self, engine):
        super().__init__()
        self.engine = engine
        self.pending_reply = None
        self.analysis_steps: list[str] = []
        self.step_index = 0
        self.current_result = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        heading = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("BLACKTERM AI ANALYST")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Grounded investigation intelligence with facts, inferences, confidence, and safe next actions.")
        subtitle.setObjectName("muted")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        heading.addLayout(title_box, 1)

        self.scan_selector = QComboBox()
        self.scan_selector.setMinimumWidth(330)
        self.scan_selector.currentIndexChanged.connect(self.load_selected_scan)
        refresh = QPushButton("REFRESH CONTEXT")
        refresh.clicked.connect(self.refresh_context)
        heading.addWidget(self.scan_selector)
        heading.addWidget(refresh)
        layout.addLayout(heading)

        metrics = QGridLayout()
        metrics.setHorizontalSpacing(10)
        self.risk_card, self.risk_value = self.metric_card("RISK", "--")
        self.confidence_card, self.confidence_value = self.metric_card("CONFIDENCE", "--")
        self.evidence_card, self.evidence_value = self.metric_card("EVIDENCE SIGNALS", "--")
        self.status_card, self.status_value = self.metric_card("ANALYST STATUS", "AWAITING DATA")
        metrics.addWidget(self.risk_card, 0, 0)
        metrics.addWidget(self.confidence_card, 0, 1)
        metrics.addWidget(self.evidence_card, 0, 2)
        metrics.addWidget(self.status_card, 0, 3)
        layout.addLayout(metrics)

        self.confidence_bar = QProgressBar()
        self.confidence_bar.setRange(0, 100)
        self.confidence_bar.setFormat("CONTEXT CONFIDENCE %p%")
        layout.addWidget(self.confidence_bar)

        quick = QHBoxLayout()
        for label, question in (
            ("SUMMARIZE", "summarize this investigation"),
            ("WHY RISKY?", "why is this risky"),
            ("CONFIRMED FACTS", "what do we know"),
            ("INFERENCES", "what might this suggest"),
            ("NEXT ACTIONS", "what should I do next"),
            ("EXECUTIVE BRIEF", "generate executive brief"),
        ):
            button = QPushButton(label)
            if label == "EXECUTIVE BRIEF":
                button.setObjectName("primary")
            button.clicked.connect(lambda _=False, q=question: self.ask_preset(q))
            quick.addWidget(button)
        layout.addLayout(quick)

        body = QHBoxLayout()
        body.setSpacing(10)

        analyst_panel = QFrame()
        analyst_panel.setObjectName("panel")
        analyst_layout = QVBoxLayout(analyst_panel)
        analyst_title = QLabel("LIVE INVESTIGATION BRIEF")
        analyst_title.setObjectName("sectionTitle")
        self.brief = QTextBrowser()
        self.brief.setOpenExternalLinks(False)
        self.brief.setStyleSheet("font-family: Consolas; font-size: 12px; padding: 10px;")
        analyst_layout.addWidget(analyst_title)
        analyst_layout.addWidget(self.brief, 1)
        copy_brief = QPushButton("COPY BRIEF")
        copy_brief.clicked.connect(self.copy_current_brief)
        analyst_layout.addWidget(copy_brief)
        body.addWidget(analyst_panel, 5)

        chat_panel = QFrame()
        chat_panel.setObjectName("panel")
        chat_layout = QVBoxLayout(chat_panel)
        chat_title = QLabel("ASK BLACKTERM")
        chat_title.setObjectName("sectionTitle")
        self.chat = QTextBrowser()
        self.chat.setOpenExternalLinks(False)
        self.chat.setStyleSheet("font-family: Consolas; font-size: 12px; padding: 10px;")
        chat_layout.addWidget(chat_title)
        chat_layout.addWidget(self.chat, 1)

        row = QHBoxLayout()
        prompt = QLabel(">")
        prompt.setStyleSheet("font-size: 22px; font-weight: 900; color: #c000ff;")
        self.input = QLineEdit()
        self.input.setPlaceholderText("Ask why it is risky, explain a service, or request next steps...")
        button = QPushButton("ANALYZE")
        button.setObjectName("primary")
        button.clicked.connect(self.ask)
        self.input.returnPressed.connect(self.ask)
        row.addWidget(prompt)
        row.addWidget(self.input, 1)
        row.addWidget(button)
        chat_layout.addLayout(row)
        body.addWidget(chat_panel, 6)
        layout.addLayout(body, 1)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.advance_analysis)
        self.show_welcome()
        self.refresh_context()

    @staticmethod
    def metric_card(label: str, initial: str):
        frame = QFrame()
        frame.setObjectName("panel")
        box = QVBoxLayout(frame)
        caption = QLabel(label)
        caption.setObjectName("muted")
        value = QLabel(initial)
        value.setStyleSheet("font-size: 19px; font-weight: 900; color: #31b7ff;")
        box.addWidget(caption)
        box.addWidget(value)
        return frame, value

    def show_welcome(self):
        self.chat.setHtml(
            """
            <div style="color:#c000ff;font-weight:900;font-size:16px;">BLACKTERM AI ANALYST ONLINE</div>
            <div style="color:#9b8aa8;margin-top:8px;line-height:1.6;">
                Analysis is grounded in the selected saved scan.<br>
                Confirmed observations are separated from contextual inference.<br><br>
                Try: <b>why is this risky?</b><br>
                Try: <b>what do we know?</b><br>
                Try: <b>explain SMB</b><br>
                Try: <b>generate executive brief</b>
            </div>
            """
        )

    def refresh_context(self):
        selected_id = self.scan_selector.currentData()
        rows = self.engine.repository.list_recent(50)
        self.scan_selector.blockSignals(True)
        self.scan_selector.clear()
        for row in rows:
            scan_id = row["id"]
            label = f"#{scan_id}  {row.get('target', 'unknown')}  •  {row.get('open_port_count', 0)} open"
            self.scan_selector.addItem(label, scan_id)
        self.scan_selector.blockSignals(False)
        if selected_id is not None:
            index = self.scan_selector.findData(selected_id)
            if index >= 0:
                self.scan_selector.setCurrentIndex(index)
        self.load_selected_scan()

    def load_selected_scan(self, *_):
        scan_id = self.scan_selector.currentData()
        self.current_result = self.engine.repository.get(scan_id) if scan_id is not None else None
        self.render_brief()

    def latest_result(self):
        return self.current_result

    def render_brief(self):
        brief = build_analyst_brief(self.current_result)
        self.risk_value.setText(f"{brief.risk_level}  {brief.risk_score}/100")
        self.confidence_value.setText(f"{brief.confidence}%")
        self.evidence_value.setText(str(brief.evidence_count))
        self.status_value.setText(brief.status)
        self.confidence_bar.setValue(brief.confidence)

        risk_color = {
            "CRITICAL": "#ff3b6b", "HIGH": "#ff3b6b", "MEDIUM": "#ffbd2e",
            "LOW": "#2ee6a6", "UNKNOWN": "#9b8aa8",
        }.get(brief.risk_level, "#31b7ff")
        self.risk_value.setStyleSheet(f"font-size:19px;font-weight:900;color:{risk_color};")

        facts = "".join(f"<li>{escape(item)}</li>" for item in brief.facts) or "<li>No confirmed observations.</li>"
        inferences = "".join(f"<li>{escape(item)}</li>" for item in brief.inferences)
        actions = "".join(f"<li>{escape(item)}</li>" for item in brief.recommendations)
        self.brief.setHtml(
            f"""
            <div style="font-family:Consolas;color:#f5efff;">
              <div style="font-size:17px;font-weight:900;color:#31b7ff;">{escape(brief.target)}</div>
              <div style="color:#9b8aa8;margin:6px 0 14px 0;">{escape(brief.summary)}</div>
              <div style="color:#2ee6a6;font-weight:900;">CONFIRMED FACTS</div>
              <ul style="line-height:1.5;">{facts}</ul>
              <div style="color:#c000ff;font-weight:900;">ANALYST INFERENCES</div>
              <ul style="line-height:1.5;">{inferences}</ul>
              <div style="color:#31b7ff;font-weight:900;">RECOMMENDED NEXT STEPS</div>
              <ul style="line-height:1.5;">{actions}</ul>
              <div style="color:#786b82;margin-top:14px;">Advisory analysis only. Exposure does not prove vulnerability.</div>
            </div>
            """
        )

    def append_card(self, sender: str, body: str, accent: str, meta: str = ""):
        meta_html = f'<div style="color:#786b82;font-size:10px;margin-bottom:6px;">{escape(meta)}</div>' if meta else ""
        html = (
            f'<div style="margin:12px 0;padding:12px 14px;border:1px solid {accent};'
            f'border-radius:10px;background:#100b17;">'
            f'<div style="color:{accent};font-weight:900;margin-bottom:6px;">{escape(sender)}</div>'
            f'{meta_html}<div style="color:#f5efff;white-space:pre-wrap;line-height:1.45;">'
            f'{escape(body).replace(chr(10), "<br>")}</div></div>'
        )
        cursor = self.chat.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertHtml(html)
        self.chat.setTextCursor(cursor)
        self.chat.ensureCursorVisible()

    def ask_preset(self, question: str):
        self.input.setText(question)
        self.ask()

    def ask(self):
        question = self.input.text().strip()
        if not question:
            return
        self.append_card("OPERATOR", question, "#31b7ff")
        self.input.clear()

        if getattr(self.engine, "event_bus", None):
            from ...events import EventLevel
            self.engine.event_bus.emit("ai", question, title="Analyst Question", level=EventLevel.AI, module="assistant")

        self.pending_reply = answer_question(question, self.latest_result())
        self.analysis_steps = [
            "Loading selected investigation context...",
            "Separating confirmed observations from inference...",
            "Calculating evidence coverage and confidence...",
            "Preparing grounded analyst response...",
        ]
        self.step_index = 0
        self.timer.start(180)

    def advance_analysis(self):
        if self.step_index < len(self.analysis_steps):
            if self.step_index == 0:
                self.append_card("BLACKTERM AI", self.analysis_steps[self.step_index], "#786b82", "ANALYSIS PIPELINE")
            self.step_index += 1
            return
        self.timer.stop()
        reply = self.pending_reply
        self.append_card(
            f"BLACKTERM AI // {reply.title}", reply.body, "#c000ff",
            f"CONFIDENCE {reply.confidence}%  •  EVIDENCE {reply.evidence_count}",
        )
        if getattr(self.engine, "event_bus", None):
            from ...events import EventLevel
            self.engine.event_bus.emit("ai", reply.body, title=reply.title, level=EventLevel.AI, module="assistant")

    def copy_current_brief(self):
        QGuiApplication.clipboard().setText(build_analyst_brief(self.current_result).to_text())
        self.status_value.setText("BRIEF COPIED")
        QTimer.singleShot(1400, self.render_brief)
