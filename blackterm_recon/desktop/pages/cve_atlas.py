from __future__ import annotations

import html
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from ...intelligence.cve_atlas import CVEAtlasClient, CVERecord

SEVERITY_COLORS = {
    "CRITICAL": "#ff4d6d",
    "HIGH": "#ff9f43",
    "MEDIUM": "#ffd166",
    "LOW": "#45d483",
    "UNKNOWN": "#7f9bb5",
}


class CVEWorker(QThread):
    completed = Signal(list)
    failed = Signal(str)

    def __init__(self, mode: str, query: str = "", parent=None):
        super().__init__(parent)
        self.mode = mode
        self.query = query

    def run(self):
        try:
            client = CVEAtlasClient()
            records = client.latest(50) if self.mode == "latest" else client.search(self.query, 50)
            self.completed.emit(records)
        except Exception as exc:
            self.failed.emit(str(exc))


class MetricCard(QFrame):
    def __init__(self, label: str, value: str = "0", accent: str = "#31b7ff", parent=None):
        super().__init__(parent)
        self.setObjectName("metricCard")
        self.setStyleSheet(
            f"QFrame#metricCard{{background:#08111f;border:1px solid #173a5a;border-radius:10px;}}"
            f"QLabel#metricValue{{font-size:20px;font-weight:900;color:{accent};}}"
            "QLabel#metricLabel{font-size:9px;font-weight:800;color:#718aa4;letter-spacing:1px;}"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(1)
        self.value = QLabel(value)
        self.value.setObjectName("metricValue")
        self.caption = QLabel(label)
        self.caption.setObjectName("metricLabel")
        layout.addWidget(self.value)
        layout.addWidget(self.caption)


class CVEAtlasPage(QWidget):
    def __init__(self, engine=None, event_bus=None, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.event_bus = event_bus
        self.records: list[CVERecord] = []
        self.filtered_records: list[CVERecord] = []
        self.current_record: CVERecord | None = None
        self.worker: CVEWorker | None = None
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(10)

        title_row = QHBoxLayout()
        heading = QVBoxLayout()
        title = QLabel("VULNERABILITY INTELLIGENCE")
        title.setStyleSheet("font-size:24px;font-weight:900;letter-spacing:1px;")
        subtitle = QLabel("CVE Atlas • CISA KEV • CVSS • MITRE context • SOC guidance")
        subtitle.setStyleSheet("color:#7f9bb5;font-size:11px;")
        heading.addWidget(title)
        heading.addWidget(subtitle)
        title_row.addLayout(heading)
        title_row.addStretch(1)
        self.status = QLabel("NVD + CISA KEV ONLINE")
        self.status.setStyleSheet("color:#36e6b0;font-weight:900;letter-spacing:.7px;")
        title_row.addWidget(self.status)
        root.addLayout(title_row)

        metrics = QHBoxLayout()
        metrics.setSpacing(8)
        self.total_card = MetricCard("RECORDS", "0")
        self.critical_card = MetricCard("CRITICAL", "0", "#ff4d6d")
        self.high_card = MetricCard("HIGH", "0", "#ff9f43")
        self.kev_card = MetricCard("KNOWN EXPLOITED", "0", "#ff4d6d")
        self.avg_card = MetricCard("AVG CVSS", "—", "#36e6b0")
        for card in (self.total_card, self.critical_card, self.high_card, self.kev_card, self.avg_card):
            metrics.addWidget(card)
        root.addLayout(metrics)

        search_panel = QFrame()
        search_panel.setObjectName("panel")
        search_layout = QHBoxLayout(search_panel)
        search_layout.setContentsMargins(10, 9, 10, 9)
        self.query = QLineEdit()
        self.query.setPlaceholderText("Search CVE ID, vendor, product, or weakness — CVE-2024-3094, Apache, XSS…")
        self.query.returnPressed.connect(self.search)
        self.severity = QComboBox()
        self.severity.addItems(["ALL SEVERITIES", "CRITICAL", "HIGH", "MEDIUM", "LOW", "UNKNOWN"])
        self.severity.currentTextChanged.connect(self.apply_filter)
        self.kev_only = QPushButton("KEV ONLY")
        self.kev_only.setCheckable(True)
        self.kev_only.toggled.connect(self.apply_filter)
        search_btn = QPushButton("SEARCH ATLAS")
        search_btn.clicked.connect(self.search)
        latest_btn = QPushButton("LATEST")
        latest_btn.clicked.connect(self.load_latest)
        export_btn = QPushButton("EXPORT")
        export_btn.clicked.connect(self.export_current)
        search_layout.addWidget(self.query, 1)
        search_layout.addWidget(self.severity)
        search_layout.addWidget(self.kev_only)
        search_layout.addWidget(search_btn)
        search_layout.addWidget(latest_btn)
        search_layout.addWidget(export_btn)
        root.addWidget(search_panel)

        splitter = QSplitter()
        splitter.setChildrenCollapsible(False)
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["CVE", "SEVERITY", "CVSS", "KEV", "PRODUCT", "PUBLISHED"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.itemSelectionChanged.connect(self.show_selected)
        splitter.addWidget(self.table)

        right = QFrame()
        right.setObjectName("panel")
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(10, 10, 10, 10)
        self.tabs = QTabWidget()
        self.overview = QTextBrowser()
        self.analysis = QTextBrowser()
        self.soc = QTextBrowser()
        self.references = QTextBrowser()
        for browser in (self.overview, self.analysis, self.soc, self.references):
            browser.setOpenExternalLinks(True)
        self.overview.setHtml(self._welcome_html())
        self.tabs.addTab(self.overview, "OVERVIEW")
        self.tabs.addTab(self.analysis, "ATTACK FLOW + MITRE")
        self.tabs.addTab(self.soc, "SOC + REMEDIATION")
        self.tabs.addTab(self.references, "REFERENCES")
        right_layout.addWidget(self.tabs)
        splitter.addWidget(right)
        splitter.setSizes([560, 900])
        root.addWidget(splitter, 1)

    def _welcome_html(self) -> str:
        return """
        <h2 style='color:#31b7ff'>BLACKTERM CVE Atlas</h2>
        <p>Search public CVE intelligence and turn raw vulnerability records into an analyst-ready view.</p>
        <p><b>Included:</b> CVSS, CISA KEV status, affected products, plain-language explanations, attack-flow modeling, MITRE context, detection ideas, remediation guidance, timelines, and source references.</p>
        <p><b>Safe by design:</b> this workspace explains vulnerability behavior and defensive validation. It does not generate weaponized payloads.</p>
        """

    def search(self):
        query = self.query.text().strip()
        if not query:
            QMessageBox.information(self, "Vulnerability Intelligence", "Enter a CVE ID, vendor, product, or weakness.")
            return
        self._start_worker("search", query)

    def load_latest(self):
        self._start_worker("latest")

    def command_lookup(self, cve_id: str):
        self.query.setText(cve_id)
        self.search()

    def command_explain(self, cve_id: str):
        self.query.setText(cve_id)
        self.search()
        self.tabs.setCurrentWidget(self.overview)

    def command_show_mitre(self):
        self.tabs.setCurrentWidget(self.analysis)

    def command_export(self):
        self.export_current()

    def _start_worker(self, mode: str, query: str = ""):
        if self.worker and self.worker.isRunning():
            return
        self.status.setText("QUERYING INTELLIGENCE SOURCES…")
        self.table.setRowCount(0)
        self.overview.setHtml("<h3>Loading vulnerability intelligence…</h3>")
        self.worker = CVEWorker(mode, query, self)
        self.worker.completed.connect(self._loaded)
        self.worker.failed.connect(self._failed)
        self.worker.start()

    def _loaded(self, records: list):
        self.records = records
        self.status.setText(f"{len(records)} RECORDS LOADED")
        self._update_metrics(records)
        self.apply_filter()
        if self.filtered_records:
            self.table.selectRow(0)
        else:
            self.overview.setHtml("<h3>No matching CVEs found.</h3>")

    def _failed(self, message: str):
        self.status.setText("SOURCE ERROR")
        safe = html.escape(message)
        self.overview.setHtml(f"<h3>CVE source unavailable</h3><p>{safe}</p><p>Check the connection and try again. Previously cached records may still be available.</p>")

    def _update_metrics(self, records: list[CVERecord]):
        scores = [r.score for r in records if r.score is not None]
        self.total_card.value.setText(str(len(records)))
        self.critical_card.value.setText(str(sum(r.severity.upper() == "CRITICAL" for r in records)))
        self.high_card.value.setText(str(sum(r.severity.upper() == "HIGH" for r in records)))
        self.kev_card.value.setText(str(sum(r.kev for r in records)))
        self.avg_card.value.setText(f"{sum(scores) / len(scores):.1f}" if scores else "—")

    def apply_filter(self, *_):
        wanted = self.severity.currentText()
        visible = self.records
        if wanted != "ALL SEVERITIES":
            visible = [r for r in visible if r.severity.upper() == wanted]
        if self.kev_only.isChecked():
            visible = [r for r in visible if r.kev]
        self.filtered_records = visible
        self.table.setRowCount(len(visible))
        for row, record in enumerate(visible):
            color = QColor(SEVERITY_COLORS.get(record.severity.upper(), "#7f9bb5"))
            cve_item = QTableWidgetItem(record.cve_id)
            cve_item.setData(Qt.UserRole, record)
            severity_item = QTableWidgetItem(record.severity)
            severity_item.setForeground(color)
            score_item = QTableWidgetItem("—" if record.score is None else f"{record.score:.1f}")
            score_item.setForeground(color)
            kev_item = QTableWidgetItem("YES" if record.kev else "NO")
            if record.kev:
                kev_item.setForeground(QColor("#ff4d6d"))
            product = record.product_summary or "See affected data"
            values = [cve_item, severity_item, score_item, kev_item, QTableWidgetItem(product), QTableWidgetItem(record.published[:10])]
            for col, item in enumerate(values):
                self.table.setItem(row, col, item)

    def show_selected(self):
        items = self.table.selectedItems()
        if not items:
            return
        record = self.table.item(items[0].row(), 0).data(Qt.UserRole)
        if not record:
            return
        self.current_record = record
        self.overview.setHtml(self._overview_html(record))
        self.analysis.setHtml(self._analysis_html(record))
        self.soc.setHtml(self._soc_html(record))
        self.references.setHtml(self._references_html(record))

    @staticmethod
    def _score_bar(score: float | None) -> str:
        if score is None:
            return "<span style='color:#7f9bb5'>Score unavailable</span>"
        filled = max(0, min(10, round(score)))
        return f"<code style='font-size:16px'>{'█' * filled}{'░' * (10 - filled)}</code> <b>{score:.1f}/10</b>"

    def _overview_html(self, r: CVERecord) -> str:
        severity_color = SEVERITY_COLORS.get(r.severity.upper(), "#7f9bb5")
        kev = "<span style='color:#ff4d6d;font-weight:900'>YES — KNOWN EXPLOITED</span>" if r.kev else "Not listed in CISA KEV"
        weaknesses = ", ".join(map(html.escape, r.weaknesses)) or "Not assigned"
        return f"""
        <h1 style='color:#31b7ff;margin-bottom:2px'>{html.escape(r.cve_id)}</h1>
        <p style='color:#7f9bb5'>{html.escape(r.product_summary or 'Affected product details available below')}</p>
        <table cellspacing='7'>
          <tr><td><b>Severity</b></td><td><span style='color:{severity_color};font-weight:900'>{html.escape(r.severity)}</span></td></tr>
          <tr><td><b>CVSS</b></td><td>{self._score_bar(r.score)}</td></tr>
          <tr><td><b>Exploitation</b></td><td>{kev}</td></tr>
          <tr><td><b>Published</b></td><td>{html.escape(r.published[:10])}</td></tr>
          <tr><td><b>Last modified</b></td><td>{html.escape(r.modified[:10])}</td></tr>
          <tr><td><b>CWE</b></td><td>{weaknesses}</td></tr>
        </table>
        <h3>WHAT HAPPENED</h3><p>{html.escape(r.description)}</p>
        <h3>HOW IT WORKS</h3><p>{html.escape(r.mechanism)}</p>
        <h3>EXPLAIN LIKE I'M NEW</h3>
        <div style='background:#0b1727;border-left:4px solid #31b7ff;padding:10px'>{html.escape(r.beginner_explanation)}</div>
        <h3>CVSS VECTOR</h3><p><code>{html.escape(r.vector or 'Not available')}</code></p>
        """

    def _analysis_html(self, r: CVERecord) -> str:
        flow = ""
        for index, stage in enumerate(r.attack_flow):
            flow += f"<div style='background:#0b1727;border:1px solid #173a5a;border-radius:7px;padding:9px;text-align:center'><b>{html.escape(stage)}</b></div>"
            if index < len(r.attack_flow) - 1:
                flow += "<div style='text-align:center;color:#31b7ff;font-size:18px'>▼</div>"
        techniques = "".join(
            f"<li><b>{html.escape(tid)}</b> — {html.escape(name)} <small style='color:#7f9bb5'>(contextual mapping)</small></li>"
            for tid, name in r.mitre_techniques
        ) or "<li>No confident ATT&amp;CK context was derived from the public description.</li>"
        timeline = f"""
        <table cellspacing='8'>
          <tr><td style='color:#31b7ff'>●</td><td><b>Published</b></td><td>{html.escape(r.published[:10] or 'Unknown')}</td></tr>
          <tr><td style='color:#31b7ff'>●</td><td><b>NVD modified</b></td><td>{html.escape(r.modified[:10] or 'Unknown')}</td></tr>
          <tr><td style='color:{'#ff4d6d' if r.kev else '#7f9bb5'}'>●</td><td><b>CISA KEV</b></td><td>{html.escape(r.kev_details.get('dateAdded', 'Not listed'))}</td></tr>
          <tr><td style='color:#36e6b0'>●</td><td><b>Remediation due</b></td><td>{html.escape(r.kev_details.get('dueDate', 'Follow vendor guidance'))}</td></tr>
        </table>
        """
        return f"""
        <h2 style='color:#31b7ff'>ATTACK FLOW</h2>{flow}
        <h2 style='color:#31b7ff'>POTENTIAL IMPACT</h2><p>{html.escape(r.impact_summary)}</p>
        <h2 style='color:#31b7ff'>MITRE ATT&amp;CK CONTEXT</h2><ul>{techniques}</ul>
        <p><small>ATT&amp;CK entries are locally inferred context, not an official mapping for this CVE. Confirm against vendor and threat-intelligence reporting.</small></p>
        <h2 style='color:#31b7ff'>TIMELINE</h2>{timeline}
        """

    def _soc_html(self, r: CVERecord) -> str:
        detections = "".join(f"<li>{html.escape(x)}</li>" for x in r.detection_ideas)
        actions = "".join(f"<li>{html.escape(x)}</li>" for x in r.defensive_actions)
        affected = "".join(f"<li><code>{html.escape(x)}</code></li>" for x in r.affected[:15]) or "<li>Use vendor references to confirm exact affected versions.</li>"
        kev_action = html.escape(r.kev_details.get("requiredAction", ""))
        kev_block = f"<h2 style='color:#ff4d6d'>CISA REQUIRED ACTION</h2><p>{kev_action}</p>" if kev_action else ""
        return f"""
        <h2 style='color:#31b7ff'>SOC DETECTION IDEAS</h2><ul>{detections}</ul>
        <h2 style='color:#31b7ff'>DEFENSIVE ACTIONS</h2><ul>{actions}</ul>
        {kev_block}
        <h2 style='color:#31b7ff'>AFFECTED PRODUCT DATA</h2><ul>{affected}</ul>
        <h2 style='color:#31b7ff'>AUTHORIZED VALIDATION</h2>
        <p>Confirm the affected product and version, reproduce only in an isolated lab or explicitly authorized scope, avoid destructive payloads, and verify remediation without disrupting service.</p>
        """

    def _references_html(self, r: CVERecord) -> str:
        refs = "".join(f"<li><a href='{html.escape(url)}'>{html.escape(url)}</a></li>" for url in r.references[:25])
        related = [x for x in self.records if x.cve_id != r.cve_id and (x.product_summary == r.product_summary or set(x.weaknesses) & set(r.weaknesses))][:8]
        related_html = "".join(f"<li><b>{html.escape(x.cve_id)}</b> — {html.escape(x.severity)} {'' if x.score is None else x.score}</li>" for x in related) or "<li>No related entries in the current result set.</li>"
        return f"""
        <h2 style='color:#31b7ff'>PRIMARY REFERENCES</h2><ul>{refs or '<li>No references supplied by NVD.</li>'}</ul>
        <h2 style='color:#31b7ff'>RELATED CVEs IN CURRENT RESULTS</h2><ul>{related_html}</ul>
        <hr><p><small>Data sources: NVD CVE API and CISA Known Exploited Vulnerabilities catalog. BLACKTERM-generated explanations and contextual mappings should be verified against vendor advisories.</small></p>
        """

    def export_current(self):
        if not self.current_record:
            QMessageBox.information(self, "Export", "Select a CVE before exporting.")
            return
        default = f"BLACKTERM-{self.current_record.cve_id}-report.html"
        path, _ = QFileDialog.getSaveFileName(self, "Export vulnerability report", default, "HTML files (*.html)")
        if not path:
            return
        report = f"""<!doctype html><html><head><meta charset='utf-8'><title>{html.escape(self.current_record.cve_id)}</title>
        <style>body{{font-family:Segoe UI,Arial;background:#07101d;color:#eaf5ff;max-width:1000px;margin:40px auto;padding:20px}}a{{color:#31b7ff}}code{{color:#36e6b0}}h1,h2,h3{{color:#31b7ff}}table{{color:#eaf5ff}}</style></head><body>
        <h1>BLACKTERM Vulnerability Intelligence</h1>{self._overview_html(self.current_record)}{self._analysis_html(self.current_record)}{self._soc_html(self.current_record)}{self._references_html(self.current_record)}</body></html>"""
        try:
            Path(path).write_text(report, encoding="utf-8")
            QMessageBox.information(self, "Export complete", f"Report saved to:\n{path}")
        except OSError as exc:
            QMessageBox.critical(self, "Export failed", str(exc))
