THEMES = {
    "Purple Void": {
        "bg": "#07050b", "panel": "#100b17", "panel2": "#171020",
        "accent": "#c000ff", "accent2": "#7f3cff", "text": "#f5efff",
        "muted": "#9b8aa8", "border": "#372342", "good": "#35df83",
        "bad": "#ff5c7a", "warn": "#ffc857",
    },
    "Green Matrix": {
        "bg": "#040806", "panel": "#07110b", "panel2": "#0c1a11",
        "accent": "#00ff75", "accent2": "#00b85b", "text": "#eafff1",
        "muted": "#7aa98a", "border": "#184b2c", "good": "#00ff75",
        "bad": "#ff5470", "warn": "#d6ff4d",
    },
    "Blue Ice": {
        "bg": "#050910", "panel": "#0a1320", "panel2": "#101d2e",
        "accent": "#31b7ff", "accent2": "#6e7dff", "text": "#edf8ff",
        "muted": "#8fa8bd", "border": "#1c3d5c", "good": "#3fe2b5",
        "bad": "#ff668a", "warn": "#ffd166",
    },
    "Blood Moon": {
        "bg": "#0d0507", "panel": "#17090d", "panel2": "#210d13",
        "accent": "#ff1744", "accent2": "#b40027", "text": "#fff0f3",
        "muted": "#b48b95", "border": "#57202e", "good": "#55e39f",
        "bad": "#ff1744", "warn": "#ffb547",
    },
    "Amber Terminal": {
        "bg": "#0b0803", "panel": "#151005", "panel2": "#211808",
        "accent": "#ffb000", "accent2": "#ff7a00", "text": "#fff6df",
        "muted": "#b9a16f", "border": "#584019", "good": "#7dea7d",
        "bad": "#ff5f57", "warn": "#ffb000",
    },
    "Midnight": {
        "bg": "#07080c", "panel": "#0d1018", "panel2": "#141927",
        "accent": "#8f95ff", "accent2": "#6570d8", "text": "#f2f4ff",
        "muted": "#9298ad", "border": "#2b3147", "good": "#52d6a7",
        "bad": "#ff6b83", "warn": "#f5c96b",
    },
}


def stylesheet(name: str) -> str:
    t = THEMES.get(name, THEMES["Purple Void"])
    return f"""
    QWidget {{
        background: transparent;
        color: {t['text']};
        font-family: 'Segoe UI';
        font-size: 13px;
    }}
    QMainWindow, QWidget#rootWindow, QStackedWidget {{
        background: {t['bg']};
    }}
    QFrame#sidebar, QFrame#panel, QFrame#glassPanel, QFrame#metricCard, QGroupBox {{
        background-color: rgba(16, 11, 23, 232);
        border: 1px solid {t['border']};
        border-radius: 12px;
    }}
    QFrame#metricCard:hover {{
        border: 1px solid {t['accent']};
        background-color: rgba(23, 16, 32, 240);
    }}
    QLabel#brand {{
        color: {t['accent']};
        font-size: 25px;
        font-weight: 900;
        letter-spacing: 1px;
    }}
    QLabel#pageTitle {{
        font-size: 25px;
        font-weight: 750;
    }}
    QLabel#metricValue {{
        color: {t['accent']};
        font-size: 32px;
        font-weight: 900;
    }}
    QLabel#muted {{
        color: {t['muted']};
    }}
    QLabel#statusActive {{
        color: {t['good']};
        font-weight: 800;
    }}
    QLabel#statusPlanned {{
        color: {t['muted']};
        font-weight: 700;
    }}
    QPushButton {{
        background: {t['panel2']};
        border: 1px solid {t['border']};
        border-radius: 8px;
        padding: 10px 13px;
        text-align: left;
    }}
    QPushButton:hover {{
        border-color: {t['accent']};
        color: {t['accent']};
    }}
    QPushButton#primary {{
        background: {t['accent']};
        color: #08060d;
        font-weight: 900;
        text-align: center;
        border: none;
    }}
    QPushButton#primary:hover {{
        background: {t['accent2']};
        color: white;
    }}
    QPushButton#dockButton {{
        font-family: Consolas;
        font-size: 17px;
        font-weight: 800;
        text-align: center;
        padding: 8px;
        border: none;
    }}
    QPushButton#dockButton:hover {{
        background: rgba(23, 16, 32, 245);
        color: {t['accent']};
        border: 1px solid {t['accent']};
    }}
    QPushButton#dockButton:checked {{
        background: {t['accent']};
        color: #08060d;
        border: none;
    }}
    QPushButton#navButton {{
        border: none;
        padding: 13px;
    }}
    QPushButton#navButton:checked {{
        background: {t['panel2']};
        color: {t['accent']};
        border-left: 3px solid {t['accent']};
    }}
    QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
        background: {t['panel2']};
        border: 1px solid {t['border']};
        border-radius: 7px;
        padding: 9px;
    }}
    QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
        border-color: {t['accent']};
    }}
    QTableWidget, QTextEdit, QListWidget {{
        background: rgba(16, 11, 23, 230);
        alternate-background-color: rgba(23, 16, 32, 235);
        border: 1px solid {t['border']};
        border-radius: 10px;
        gridline-color: {t['border']};
        selection-background-color: {t['accent2']};
    }}
    QHeaderView::section {{
        background: {t['panel2']};
        color: {t['text']};
        border: none;
        border-bottom: 1px solid {t['border']};
        padding: 9px;
        font-weight: 800;
    }}
    QProgressBar {{
        background: {t['panel2']};
        border: 1px solid {t['border']};
        border-radius: 7px;
        min-height: 16px;
        text-align: center;
    }}
    QProgressBar::chunk {{
        background: {t['accent']};
        border-radius: 6px;
    }}
    QScrollBar:vertical {{
        background: transparent;
        width: 10px;
    }}
    QScrollBar::handle:vertical {{
        background: {t['border']};
        border-radius: 5px;
        min-height: 30px;
    }}
    """
