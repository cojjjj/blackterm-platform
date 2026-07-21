from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout, QLabel, QLineEdit,
    QMessageBox, QPushButton, QSpinBox, QVBoxLayout, QWidget
)

from ...config import save_config
from ..theme import THEMES


class SettingsPage(QWidget):
    theme_changed = Signal(str)

    def __init__(self, engine):
        super().__init__()
        self.engine = engine
        root = QVBoxLayout(self)
        title = QLabel("Settings")
        title.setObjectName("pageTitle")
        root.addWidget(title)

        form = QFormLayout()
        self.workers = QSpinBox()
        self.workers.setRange(1, 1000)
        self.workers.setValue(engine.config.workers)

        self.timeout = QDoubleSpinBox()
        self.timeout.setRange(0.05, 30)
        self.timeout.setSingleStep(0.05)
        self.timeout.setValue(engine.config.timeout)

        self.banner_timeout = QDoubleSpinBox()
        self.banner_timeout.setRange(0.05, 30)
        self.banner_timeout.setValue(engine.config.banner_timeout)

        self.banners = QCheckBox()
        self.banners.setChecked(engine.config.banners)

        self.theme = QComboBox()
        self.theme.addItems(THEMES.keys())
        self.theme.setCurrentText(engine.config.theme)

        self.threat_timeout = QDoubleSpinBox()
        self.threat_timeout.setRange(2, 60)
        self.threat_timeout.setValue(getattr(engine.config, "threat_timeout", 8.0))

        self.virustotal_api_key = QLineEdit()
        self.virustotal_api_key.setEchoMode(QLineEdit.Password)
        self.virustotal_api_key.setText(getattr(engine.config, "virustotal_api_key", ""))
        self.virustotal_api_key.setPlaceholderText("Optional")

        self.abuseipdb_api_key = QLineEdit()
        self.abuseipdb_api_key.setEchoMode(QLineEdit.Password)
        self.abuseipdb_api_key.setText(getattr(engine.config, "abuseipdb_api_key", ""))
        self.abuseipdb_api_key.setPlaceholderText("Optional")

        self.case_open_behavior = QComboBox()
        self.case_open_behavior.addItem("Ask after every scan", "ask")
        self.case_open_behavior.addItem("Always open the new case", "always")
        self.case_open_behavior.addItem("Stay on the scan page", "never")
        current_behavior = getattr(engine.config, "case_open_behavior", "ask")
        index = self.case_open_behavior.findData(current_behavior)
        self.case_open_behavior.setCurrentIndex(max(index, 0))

        form.addRow("Workers", self.workers)
        form.addRow("Connection timeout", self.timeout)
        form.addRow("Banner timeout", self.banner_timeout)
        form.addRow("Banner detection", self.banners)
        form.addRow("Theme", self.theme)
        form.addRow("Threat provider timeout", self.threat_timeout)
        form.addRow("VirusTotal API key", self.virustotal_api_key)
        form.addRow("AbuseIPDB API key", self.abuseipdb_api_key)
        form.addRow("After autonomous scan", self.case_open_behavior)
        root.addLayout(form)

        save = QPushButton("SAVE SETTINGS")
        save.setObjectName("primary")
        save.clicked.connect(self.save)
        root.addWidget(save)
        root.addStretch()

    def save(self):
        config = self.engine.config
        config.workers = self.workers.value()
        config.timeout = self.timeout.value()
        config.banner_timeout = self.banner_timeout.value()
        config.banners = self.banners.isChecked()
        config.theme = self.theme.currentText()
        config.case_open_behavior = self.case_open_behavior.currentData()
        config.threat_timeout = self.threat_timeout.value()
        config.virustotal_api_key = self.virustotal_api_key.text().strip()
        config.abuseipdb_api_key = self.abuseipdb_api_key.text().strip()
        save_config(config)
        self.theme_changed.emit(config.theme)
        QMessageBox.information(self, "Settings", "Settings saved.")
