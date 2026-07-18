from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout, QLabel,
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

        form.addRow("Workers", self.workers)
        form.addRow("Connection timeout", self.timeout)
        form.addRow("Banner timeout", self.banner_timeout)
        form.addRow("Banner detection", self.banners)
        form.addRow("Theme", self.theme)
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
        save_config(config)
        self.theme_changed.emit(config.theme)
        QMessageBox.information(self, "Settings", "Settings saved.")
