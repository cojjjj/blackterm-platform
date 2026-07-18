import os
from PySide6.QtWidgets import QHBoxLayout,QLabel,QPushButton,QTableWidget,QTableWidgetItem,QVBoxLayout,QWidget

class PluginsPage(QWidget):
    def __init__(self, engine):
        super().__init__(); self.engine=engine; layout=QVBoxLayout(self); top=QHBoxLayout(); title=QLabel("Plugin Manager"); title.setObjectName("pageTitle"); reload=QPushButton("RELOAD"); folder=QPushButton("OPEN PLUGIN FOLDER"); reload.clicked.connect(self.refresh); folder.clicked.connect(self.open_folder); top.addWidget(title); top.addStretch(); top.addWidget(folder); top.addWidget(reload); layout.addLayout(top); note=QLabel("Drop authorized enrichment plugins into the folder. Invalid plugins are isolated and logged."); note.setObjectName("muted"); layout.addWidget(note); self.table=QTableWidget(0,5); self.table.setHorizontalHeaderLabels(["STATUS","NAME","VERSION","DESCRIPTION","FILE"]); self.table.horizontalHeader().setStretchLastSection(True); layout.addWidget(self.table); self.refresh()
    def refresh(self):
        plugins=self.engine.plugins.discover(); self.table.setRowCount(0)
        for plugin in plugins:
            row=self.table.rowCount(); self.table.insertRow(row)
            for column,value in enumerate(["ENABLED",plugin.name,plugin.version,plugin.description,plugin.path.name]): self.table.setItem(row,column,QTableWidgetItem(str(value)))
        self.table.resizeColumnsToContents()
    def open_folder(self):
        if hasattr(os,"startfile"): os.startfile(self.engine.config.plugin_directory)
