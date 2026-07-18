from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout,
    QLabel, QLineEdit, QMessageBox, QPushButton, QSplitter,
    QTableWidget, QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget
)
from PySide6.QtCore import Qt


class NewCaseDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create Investigation")
        layout = QFormLayout(self)
        self.name = QLineEdit()
        self.description = QTextEdit()
        self.description.setMaximumHeight(110)
        layout.addRow("Case name", self.name)
        layout.addRow("Scope / description", self.description)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)


class CasesPage(QWidget):
    def __init__(self, engine):
        super().__init__()
        self.engine = engine
        root = QVBoxLayout(self)

        top = QHBoxLayout()
        title = QLabel("Investigation Cases")
        title.setObjectName("pageTitle")
        create = QPushButton("NEW CASE")
        create.setObjectName("primary")
        create.clicked.connect(self.create_case)
        top.addWidget(title)
        top.addStretch()
        top.addWidget(create)
        root.addLayout(top)

        splitter = QSplitter(Qt.Horizontal)
        left = QWidget()
        left_layout = QVBoxLayout(left)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["ID", "NAME", "STATUS", "SCANS", "CREATED"])
        self.table.itemSelectionChanged.connect(self.show_case)
        left_layout.addWidget(self.table)

        attach_row = QHBoxLayout()
        self.scan_choice = QComboBox()
        attach = QPushButton("ATTACH SCAN")
        attach.clicked.connect(self.attach_scan)
        attach_row.addWidget(self.scan_choice, 1)
        attach_row.addWidget(attach)
        left_layout.addLayout(attach_row)
        splitter.addWidget(left)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.addWidget(QLabel("CASE WORKSPACE"))
        self.details = QTextEdit()
        self.details.setReadOnly(True)
        right_layout.addWidget(self.details, 2)

        right_layout.addWidget(QLabel("ADD NOTE"))
        self.note = QTextEdit()
        self.note.setPlaceholderText("Document observations, scope, evidence references, or next steps...")
        self.note.setMaximumHeight(120)
        save_note = QPushButton("SAVE NOTE")
        save_note.clicked.connect(self.add_note)
        right_layout.addWidget(self.note)
        right_layout.addWidget(save_note)
        splitter.addWidget(right)
        splitter.setSizes([760, 520])
        root.addWidget(splitter, 1)
        self.refresh()

    def selected_case_id(self):
        items = self.table.selectedItems()
        if not items:
            return None
        return int(self.table.item(items[0].row(), 0).text())

    def create_case(self):
        dialog = NewCaseDialog(self)
        if dialog.exec() != QDialog.Accepted:
            return
        name = dialog.name.text().strip()
        if not name:
            QMessageBox.warning(self, "Case", "A case name is required.")
            return
        case_id = self.engine.repository.create_case(
            name, dialog.description.toPlainText()
        )
        if getattr(self.engine, "event_bus", None):
            from ...events import EventLevel
            self.engine.event_bus.emit(
                "case", f"Created investigation case: {name}.",
                title="Case Created", level=EventLevel.SUCCESS,
                module="cases", metadata={"case_id": case_id},
            )
        self.refresh()

    def attach_scan(self):
        case_id = self.selected_case_id()
        scan_id = self.scan_choice.currentData()
        if case_id is None or scan_id is None:
            QMessageBox.warning(self, "Case", "Select a case and scan first.")
            return
        self.engine.repository.attach_scan_to_case(case_id, int(scan_id))
        if getattr(self.engine, "event_bus", None):
            from ...events import EventLevel
            self.engine.event_bus.emit(
                "case", f"Attached scan #{scan_id} to case #{case_id}.",
                title="Scan Attached", level=EventLevel.SUCCESS,
                module="cases", scan_id=int(scan_id),
                metadata={"case_id": case_id},
            )
        self.refresh()
        self.show_case()

    def add_note(self):
        case_id = self.selected_case_id()
        text = self.note.toPlainText().strip()
        if case_id is None or not text:
            QMessageBox.warning(self, "Case Note", "Select a case and enter a note.")
            return
        self.engine.repository.add_case_note(case_id, text)
        if getattr(self.engine, "event_bus", None):
            from ...events import EventLevel
            self.engine.event_bus.emit(
                "case", "A new investigation note was saved.",
                title="Case Note Added", level=EventLevel.INFO,
                module="cases", metadata={"case_id": case_id},
            )
        self.note.clear()
        self.show_case()

    def refresh(self):
        cases = self.engine.repository.list_cases()
        self.table.setRowCount(0)
        for case in cases:
            row = self.table.rowCount()
            self.table.insertRow(row)
            values = [
                case["id"], case["name"], case["status"],
                case["scan_count"], case["created_at"],
            ]
            for col, value in enumerate(values):
                self.table.setItem(row, col, QTableWidgetItem(str(value)))
        self.table.resizeColumnsToContents()

        self.scan_choice.clear()
        for scan in self.engine.repository.list_recent(100):
            self.scan_choice.addItem(
                f"Scan #{scan['id']} — {scan['target']} ({scan['open_ports']} open)",
                scan["id"],
            )

    def show_case(self):
        case_id = self.selected_case_id()
        if case_id is None:
            return
        case = next(
            (item for item in self.engine.repository.list_cases() if item["id"] == case_id),
            None,
        )
        scans = self.engine.repository.case_scans(case_id)
        notes = self.engine.repository.case_notes(case_id)

        lines = [
            f"CASE #{case_id}",
            f"Name: {case['name'] if case else 'Unknown'}",
            f"Status: {case['status'] if case else 'Unknown'}",
            f"Created: {case['created_at'] if case else 'Unknown'}",
            "",
            "SCOPE",
            case["description"] if case and case["description"] else "No description.",
            "",
            "ATTACHED SCANS",
        ]
        lines.extend(
            f"• #{scan['id']} {scan['target']} {scan['ip']} — {scan['open_ports']} open"
            for scan in scans
        )
        if not scans:
            lines.append("No scans attached.")

        lines.extend(["", "CASE NOTES"])
        lines.extend(
            f"{note['created_at']}\n{note['note']}\n"
            for note in notes
        )
        if not notes:
            lines.append("No notes recorded.")
        self.details.setPlainText("\n".join(lines))
