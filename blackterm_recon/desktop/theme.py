THEMES = {
    "Purple Void": {
        "bg": "#050713", "panel": "#090d1b", "panel2": "#131a31",
        "accent": "#c000ff", "accent2": "#842be2", "text": "#f4f1ff",
        "muted": "#8994ad", "border": "#2d2850", "good": "#00ef9b",
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
        font-family: 'Segoe UI Variable', 'Segoe UI';
        font-size: 13px;
    }}
    QMainWindow, QWidget#rootWindow, QStackedWidget {{
        background: {t['bg']};
    }}
    QFrame#sidebar, QFrame#panel, QFrame#glassPanel, QFrame#metricCard, QGroupBox {{
        background-color: rgba(16, 11, 23, 232);
        border: 1px solid {t['border']};
        border-radius: 10px;
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


# BLACKTERM v10.8 identity layer
IDENTITY_QSS = """
QToolTip { background:#131a31; color:#f4f1ff; border:1px solid #6c32a0; padding:6px; }
QTabWidget::pane { border:1px solid #2d2850; border-radius:9px; background:#090d1b; }
QTabBar::tab { background:#090d1b; color:#8994ad; padding:10px 16px; border:1px solid #2d2850; }
QTabBar::tab:selected { color:#f4f1ff; border-color:#a82be2; background:#17112a; }
QMenu { background:#090d1b; border:1px solid #2d2850; padding:6px; }
QMenu::item:selected { background:#842be2; color:white; }
"""

_original_stylesheet = stylesheet
def stylesheet(name: str) -> str:
    return _original_stylesheet(name) + IDENTITY_QSS + V11_WORKSPACE_QSS

# BLACKTERM X v11.0 global workspace surfaces
V11_WORKSPACE_QSS = r"""
QFrame#aiAnalystDock, QFrame#notificationCenter {
    background: rgba(7, 8, 18, 246);
    border: 1px solid #7b2bc5;
    border-radius: 13px;
}
QLabel#aiDockTitle, QLabel#notificationTitle {
    color: #d6a6ff;
    font-size: 13px;
    font-weight: 900;
    letter-spacing: 1px;
}
QLabel#aiDockStatus { color: #36e6b0; font-size: 10px; font-weight: 900; }
QTextBrowser#aiDockChat, QListWidget#notificationList {
    background: #070a13;
    border: 1px solid #242747;
    border-radius: 10px;
    color: #edf4ff;
    padding: 8px;
}
QPushButton#aiQuickAction {
    background: #10152a; color: #c9a4ff; border: 1px solid #563181;
    border-radius: 7px; padding: 7px; font-size: 9px; font-weight: 800;
}
QPushButton#aiQuickAction:hover { background: #27113f; border-color: #b12cff; }
QFrame#liveStatusBar {
    background: rgba(5, 9, 20, 225);
    border: 1px solid #1c4566;
    border-radius: 9px;
}
QLabel#liveStatusItem { color: #35dfb1; font-size: 9px; font-weight: 800; letter-spacing: .5px; }
QLabel#liveStatusClock { color: #9aaac0; font-family: Consolas; font-size: 9px; }
"""
