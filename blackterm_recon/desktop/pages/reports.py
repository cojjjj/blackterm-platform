import webbrowser
from PySide6.QtWidgets import QFileDialog,QHBoxLayout,QLabel,QMessageBox,QPushButton,QTableWidget,QTableWidgetItem,QVBoxLayout,QWidget
from ...reporting import write_html,write_pdf

class ReportsPage(QWidget):
    def __init__(self, engine):
        super().__init__(); self.engine=engine; layout=QVBoxLayout(self); header=QHBoxLayout(); title=QLabel("Report Center"); title.setObjectName("pageTitle"); refresh=QPushButton("REFRESH"); refresh.clicked.connect(self.refresh); header.addWidget(title); header.addStretch(); header.addWidget(refresh); layout.addLayout(header); self.table=QTableWidget(0,5); self.table.setHorizontalHeaderLabels(["ID","TARGET","IP","OPEN","FINISHED"]); self.table.horizontalHeader().setStretchLastSection(True); layout.addWidget(self.table,1); actions=QHBoxLayout(); html=QPushButton("OPEN HTML REPORT"); pdf=QPushButton("EXPORT PDF"); html.clicked.connect(self.open_html); pdf.clicked.connect(self.export_pdf); actions.addWidget(html); actions.addWidget(pdf); actions.addStretch(); layout.addLayout(actions); self.refresh()
    def refresh(self):
        self.table.setRowCount(0)
        for data in self.engine.repository.list_recent(100):
            row=self.table.rowCount(); self.table.insertRow(row)
            for column,value in enumerate([data["id"],data["target"],data["ip"],data["open_ports"],data["finished_at"]]): self.table.setItem(row,column,QTableWidgetItem(str(value)))
    def selected_result(self):
        items=self.table.selectedItems()
        if not items: QMessageBox.information(self,"Report Center","Select a scan first."); return None
        return self.engine.repository.get(int(self.table.item(items[0].row(),0).text()))
    def open_html(self):
        result=self.selected_result()
        if result: webbrowser.open(write_html(result).resolve().as_uri())
    def export_pdf(self):
        result=self.selected_result()
        if not result: return
        name,_=QFileDialog.getSaveFileName(self,"Export PDF",f"blackterm_scan_{result.ip}.pdf","PDF Files (*.pdf)")
        if name: write_pdf(result,name); QMessageBox.information(self,"Report Center",f"Saved {name}")
