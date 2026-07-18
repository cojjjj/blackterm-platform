from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem,
    QTextEdit, QVBoxLayout, QWidget
)


class HistoryPage(QWidget):
    def __init__(self, engine):
        super().__init__()
        self.engine = engine
        root = QVBoxLayout(self)
        top = QHBoxLayout()
        title = QLabel("Scan History")
        title.setObjectName("pageTitle")
        refresh = QPushButton("REFRESH")
        refresh.clicked.connect(self.refresh)
        top.addWidget(title)
        top.addStretch()
        top.addWidget(refresh)
        root.addLayout(top)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["ID", "TARGET", "IP", "HOSTNAME", "OPEN", "FINISHED"]
        )
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.itemSelectionChanged.connect(self.show_selected)
        root.addWidget(self.table, 3)

        self.details = QTextEdit()
        self.details.setReadOnly(True)
        root.addWidget(self.details, 2)
        self.refresh()

    def refresh(self):
        rows = self.engine.repository.list_recent(100)
        self.table.setRowCount(0)
        for row_data in rows:
            row = self.table.rowCount()
            self.table.insertRow(row)
            values = [
                row_data["id"], row_data["target"], row_data["ip"],
                row_data["hostname"] or "Unknown", row_data["open_ports"],
                row_data["finished_at"],
            ]
            for col, value in enumerate(values):
                self.table.setItem(row, col, QTableWidgetItem(str(value)))
        self.table.resizeColumnsToContents()

    def show_selected(self):
        selected = self.table.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        scan_id = int(self.table.item(row, 0).text())
        result = self.engine.repository.get(scan_id)
        if result is None:
            return
        lines = [
            f"SCAN #{scan_id}",
            f"Target: {result.target}",
            f"IP: {result.ip}",
            f"Hostname: {result.hostname or 'Unknown'}",
            f"Duration: {result.duration_seconds}s",
            "",
            "OPEN PORTS",
        ]
        lines.extend(
            f"{p.port}/tcp  {p.service}  {p.latency_ms} ms"
            for p in result.open_ports
        )
        events = self.engine.repository.get_events(scan_id)
        lines.extend(["", "TIMELINE"])
        if events:
            lines.extend(
                f"{event['event_time']}  [{event['event_type']}]  {event['message']}"
                for event in events
            )
        else:
            lines.extend([
                f"{result.started_at}  [START]  Scan started",
                *[
                    f"{result.finished_at}  [OPEN]  {p.port}/tcp {p.service}"
                    for p in result.open_ports
                ],
                f"{result.finished_at}  [DONE]  Scan completed",
            ])
        self.details.setPlainText("\n".join(lines))
