from __future__ import annotations


PREMIUM_STYLESHEET = r"""
/* BLACKTERM v8.5 premium visual layer */

QMainWindow, QWidget#rootWindow {
    background: #050912;
    color: #edf6ff;
}

QWidget {
    selection-background-color: #174d73;
    selection-color: #ffffff;
}

QFrame#panel,
QFrame#operatorResume,
QFrame#operatorAwareness,
QFrame#operatorRecent {
    background: rgba(11, 10, 20, 238);
    border: 1px solid #274766;
    border-radius: 12px;
}

QFrame#panel:hover,
QFrame#operatorResume:hover,
QFrame#operatorAwareness:hover,
QFrame#operatorRecent:hover {
    border-color: #3b739e;
}

QLabel#pageTitle {
    color: #f7fbff;
    font-size: 25px;
    font-weight: 900;
}

QLabel#sectionTitle {
    color: #41c7ff;
    font-weight: 900;
    letter-spacing: 0.5px;
}

QLabel#muted {
    color: #8ea5be;
}

QLabel#metricValue {
    color: #35baff;
    font-size: 27px;
    font-weight: 900;
}

QPushButton {
    min-height: 32px;
    padding: 7px 14px;
    border: 1px solid #285273;
    border-radius: 9px;
    background: #0c1a2a;
    color: #eaf5ff;
    font-weight: 750;
}

QPushButton:hover {
    border-color: #49c9ff;
    background: #112941;
    color: #ffffff;
}

QPushButton:pressed {
    background: #0a2035;
    padding-top: 8px;
    padding-bottom: 6px;
}

QPushButton:disabled {
    color: #5f7185;
    border-color: #1a3046;
    background: #09121d;
}

QPushButton#primary {
    color: #04111c;
    border: 1px solid #47d7ff;
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 #31b7ff,
        stop:0.55 #37c9f7,
        stop:1 #36e6b0
    );
    font-weight: 900;
}

QPushButton#primary:hover {
    border-color: #9beaff;
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 #55c8ff,
        stop:0.55 #52dcfa,
        stop:1 #58f0c5
    );
}

QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QListWidget, QTableWidget {
    background: rgba(6, 12, 22, 242);
    color: #eef7ff;
    border: 1px solid #244664;
    border-radius: 8px;
    padding: 7px;
}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus,
QListWidget:focus, QTableWidget:focus {
    border: 1px solid #31b7ff;
}

QCheckBox {
    spacing: 7px;
    color: #c9d7e6;
    font-weight: 650;
}

QCheckBox::indicator {
    width: 15px;
    height: 15px;
    border: 1px solid #3b617f;
    border-radius: 4px;
    background: #08111c;
}

QCheckBox::indicator:checked {
    border-color: #36e6b0;
    background: #36e6b0;
}

QProgressBar {
    min-height: 14px;
    border: 1px solid #28516f;
    border-radius: 7px;
    background: #091522;
    color: #ffffff;
    text-align: center;
    font-size: 9px;
    font-weight: 800;
}

QProgressBar::chunk {
    border-radius: 6px;
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 #31b7ff,
        stop:0.58 #27c6ee,
        stop:1 #b000ff
    );
}

QTabWidget::pane {
    border: 1px solid #243f5d;
    border-radius: 9px;
    background: rgba(7, 9, 17, 230);
}

QTabBar::tab {
    min-height: 28px;
    padding: 6px 12px;
    margin-right: 2px;
    color: #a9bad0;
    background: #090d16;
    border: 1px solid #172b40;
    border-bottom: none;
    border-top-left-radius: 7px;
    border-top-right-radius: 7px;
}

QTabBar::tab:hover {
    color: #ffffff;
    background: #102238;
    border-color: #315d82;
}

QTabBar::tab:selected {
    color: #ffffff;
    background: #151224;
    border-color: #7940a0;
}

QHeaderView::section {
    background: #101d2d;
    color: #f2f8ff;
    border: none;
    border-bottom: 1px solid #31577f;
    padding: 8px;
    font-weight: 850;
}

QTableWidget {
    alternate-background-color: #0d0a16;
    gridline-color: #19334b;
}

QTableWidget::item {
    padding: 7px;
    border-bottom: 1px solid #162b40;
}

QTableWidget::item:hover {
    background: #10263b;
}

QTableWidget::item:selected {
    background: #174b70;
    color: #ffffff;
}

QListWidget::item {
    min-height: 26px;
    padding: 6px 8px;
    margin: 1px 0;
    border-radius: 6px;
}

QListWidget::item:hover {
    background: #10263b;
}

QListWidget::item:selected {
    background: #183f5f;
    color: #ffffff;
}

QScrollBar:vertical {
    width: 10px;
    background: #080e17;
    margin: 2px;
}

QScrollBar::handle:vertical {
    min-height: 32px;
    border-radius: 5px;
    background: #31577b;
}

QScrollBar::handle:vertical:hover {
    background: #4384ae;
}

QScrollBar:horizontal {
    height: 10px;
    background: #080e17;
    margin: 2px;
}

QScrollBar::handle:horizontal {
    min-width: 32px;
    border-radius: 5px;
    background: #31577b;
}

QToolTip {
    color: #f4f9ff;
    background: #0a1421;
    border: 1px solid #3f7299;
    padding: 6px;
}

/* Intelligence Engine */
QFrame#intelligenceLaunch,
QFrame#intelligenceTelemetry,
QFrame#intelligencePipeline,
QFrame#intelligenceAnalysis {
    background: rgba(10, 10, 19, 242);
    border: 1px solid #294c6c;
    border-radius: 12px;
}

QFrame#intelligenceLaunch {
    border-top: 2px solid #31b7ff;
}

QFrame#intelligenceTelemetry {
    border-top: 2px solid #36e6b0;
}

QFrame#intelligencePipeline {
    border-left: 3px solid #31b7ff;
}

QFrame#intelligenceAnalysis {
    border-left: 3px solid #b000ff;
}

QLabel#liveReady {
    padding: 6px 11px;
    border-radius: 10px;
    background: #102b2b;
    color: #36e6b0;
    font-weight: 900;
}

QLabel#liveActive {
    padding: 6px 11px;
    border-radius: 10px;
    background: #2c1537;
    color: #e299ff;
    font-weight: 900;
}

QLabel#liveComplete {
    padding: 6px 11px;
    border-radius: 10px;
    background: #102b2b;
    color: #36e6b0;
    font-weight: 900;
}
"""


def premium_stylesheet() -> str:
    return PREMIUM_STYLESHEET
