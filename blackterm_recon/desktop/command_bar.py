from __future__ import annotations

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QLineEdit


class CommandBar(QFrame):
    def __init__(self, execute_callback):
        super().__init__()
        self.setObjectName("panel")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        prompt = QLabel("blackterm>")
        prompt.setStyleSheet("font-family: Consolas; color: #c000ff; font-weight: 900;")
        self.input = QLineEdit()
        self.input.setPlaceholderText("open dashboard | open scan | open map | open assistant | history")
        self.input.returnPressed.connect(self.execute)
        self.execute_callback = execute_callback
        layout.addWidget(prompt)
        layout.addWidget(self.input, 1)

    def execute(self):
        command = self.input.text().strip()
        if command:
            self.execute_callback(command)
            self.input.clear()
