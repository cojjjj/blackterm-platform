from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QFrame,
    QLabel, QLineEdit, QMessageBox, QVBoxLayout,
)

from ..autonomous_workflow import AutonomousWorkflowOptions


class InvestigationWizard(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("BLACKTERM // New Autonomous Investigation")
        self.setModal(True)
        self.setMinimumWidth(560)
        root = QVBoxLayout(self)
        title = QLabel("NEW AUTONOMOUS INVESTIGATION")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Create one case and run selected authorized intelligence stages end to end.")
        subtitle.setObjectName("muted")
        root.addWidget(title)
        root.addWidget(subtitle)

        panel = QFrame()
        panel.setObjectName("panel")
        form = QFormLayout(panel)
        self.name = QLineEdit(f"Operation {datetime.now():%Y-%m-%d %H:%M}")
        self.target = QLineEdit()
        self.target.setPlaceholderText("Authorized domain, IP address, or hostname")
        self.profile = QComboBox()
        self.profile.addItem("Quick", "quick")
        self.profile.addItem("Standard", "standard")
        self.profile.addItem("Full (controlled environments)", "full")
        self.profile.setCurrentIndex(1)
        form.addRow("OPERATION NAME", self.name)
        form.addRow("TARGET", self.target)
        form.addRow("RECON PROFILE", self.profile)

        self.recon = QCheckBox("Reconnaissance and attack-surface collection")
        self.osint = QCheckBox("OSINT enrichment")
        self.threat = QCheckBox("Threat intelligence correlation")
        self.correlation = QCheckBox("AI cross-module correlation")
        self.report = QCheckBox("Generate HTML case report")
        for box in (self.recon, self.osint, self.threat, self.correlation, self.report):
            box.setChecked(True)
            form.addRow("", box)
        self.authorization = QCheckBox(
            "I confirm that I own this target or have explicit authorization to assess it."
        )
        self.authorization.setObjectName("authorizationCheck")
        form.addRow("AUTHORIZATION", self.authorization)
        root.addWidget(panel)

        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        self.start_button = self.buttons.addButton("START INVESTIGATION", QDialogButtonBox.ButtonRole.AcceptRole)
        self.start_button.setObjectName("primary")
        self.buttons.rejected.connect(self.reject)
        self.buttons.accepted.connect(self._validate)
        root.addWidget(self.buttons)

    def _validate(self):
        if not self.target.text().strip():
            QMessageBox.warning(self, "Target required", "Enter an authorized target.")
            return
        if not self.authorization.isChecked():
            QMessageBox.warning(self, "Authorization required", "Confirm explicit authorization before continuing.")
            return
        if not any((self.recon.isChecked(), self.osint.isChecked(), self.threat.isChecked(), self.correlation.isChecked(), self.report.isChecked())):
            QMessageBox.warning(self, "No stages selected", "Select at least one workflow stage.")
            return
        self.accept()

    def options(self) -> AutonomousWorkflowOptions:
        return AutonomousWorkflowOptions(
            operation_name=self.name.text().strip(),
            target=self.target.text().strip(),
            profile=str(self.profile.currentData()),
            run_recon=self.recon.isChecked(),
            run_osint=self.osint.isChecked(),
            run_threat_intelligence=self.threat.isChecked(),
            run_ai_correlation=self.correlation.isChecked(),
            generate_report=self.report.isChecked(),
        )
