from PySide6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton,
    QVBoxLayout, QWidget
)

from ..modules import MODULES
from ..widgets import add_glow


class PlatformPage(QWidget):
    def __init__(self, navigate):
        super().__init__()
        self.navigate = navigate
        root = QVBoxLayout(self)

        title = QLabel("BLACKTERM Platform")
        title.setObjectName("pageTitle")
        subtitle = QLabel(
            "One extensible shell for authorized security workflows, cases, intelligence, and reports."
        )
        subtitle.setObjectName("muted")
        root.addWidget(title)
        root.addWidget(subtitle)

        grid = QGridLayout()
        for index, module in enumerate(MODULES):
            card = QFrame()
            card.setObjectName("panel")
            add_glow(card, blur=18, alpha=26)
            layout = QVBoxLayout(card)
            name = QLabel(module.title)
            name.setStyleSheet("font-size: 18px; font-weight: 850;")
            status = QLabel(module.status)
            status.setObjectName(
                "statusActive" if module.status in {"ACTIVE", "ACTIVE BETA", "READY FOR INTEGRATION"}
                else "statusPlanned"
            )
            description = QLabel(module.description)
            description.setObjectName("muted")
            description.setWordWrap(True)
            layout.addWidget(name)
            layout.addWidget(status)
            layout.addWidget(description)
            layout.addStretch()

            button = QPushButton("OPEN MODULE" if module.command else "VIEW SDK STATUS")
            if module.command:
                button.setObjectName("primary")
                button.clicked.connect(
                    lambda checked=False, command=module.command: self.navigate(command)
                )
            else:
                button.clicked.connect(
                    lambda checked=False, title=module.title: self.show_roadmap(title)
                )
            layout.addWidget(button)
            grid.addWidget(card, index // 3, index % 3)

        root.addLayout(grid, 1)

    def show_roadmap(self, title):
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.information(
            self,
            title,
            f"{title} has an SDK-ready integration slot in the shared platform. "
            "Its specialized engine is not included in this RECON release yet.",
        )
