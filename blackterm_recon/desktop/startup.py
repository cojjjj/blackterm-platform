from __future__ import annotations
from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QTimer, Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtWidgets import QDialog, QFrame, QHBoxLayout, QLabel, QLineEdit, QProgressBar, QPushButton, QStackedLayout, QVBoxLayout, QWidget
from .branding import LOGO_PATH, SoundIdentity

class StartupSequence(QDialog):
    accepted_operator = Signal(str)
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BLACKTERM")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(940, 580)
        self.sound = SoundIdentity(self)
        shell = QFrame(); shell.setObjectName("identityShell")
        shell.setStyleSheet("""
        QFrame#identityShell{background:#050713;border:1px solid #38235b;border-radius:22px;}
        QLabel{color:#f4f1ff;background:transparent;} QLineEdit{background:#090d1b;color:#f4f1ff;border:1px solid #342958;border-radius:9px;padding:12px;}
        QPushButton{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #842be2,stop:.55 #c000ff,stop:1 #00e5ff);color:#050713;font-weight:900;border:0;border-radius:9px;padding:12px;}
        QProgressBar{background:#090d1b;border:1px solid #342958;border-radius:6px;text-align:center;color:#9ea9c0;}
        QProgressBar::chunk{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #842be2,stop:.65 #c000ff,stop:1 #00e5ff);border-radius:5px;}
        """)
        outer=QVBoxLayout(self); outer.setContentsMargins(0,0,0,0); outer.addWidget(shell)
        self.stack=QStackedLayout(shell)
        boot=QWidget(); lay=QHBoxLayout(boot); lay.setContentsMargins(52,46,52,46); lay.setSpacing(42)
        logo_col=QVBoxLayout(); logo=QSvgWidget(str(LOGO_PATH)); logo.setFixedSize(260,260); logo_col.addStretch(); logo_col.addWidget(logo,0,Qt.AlignCenter)
        brand=QLabel("BLACKTERM"); brand.setAlignment(Qt.AlignCenter); brand.setStyleSheet("font-size:28px;font-weight:950;letter-spacing:5px;color:#f4f1ff;")
        tag=QLabel("INVESTIGATION OS"); tag.setAlignment(Qt.AlignCenter); tag.setStyleSheet("font-size:10px;font-weight:900;letter-spacing:4px;color:#b64cff;")
        logo_col.addWidget(brand); logo_col.addWidget(tag); logo_col.addStretch(); lay.addLayout(logo_col,1)
        right=QVBoxLayout(); badge=QLabel("BLACKTERM // SECURE BOOT"); badge.setStyleSheet("font-size:10px;font-weight:900;letter-spacing:2px;color:#00e5ff;")
        self.current_module=QLabel("INITIALIZING"); self.current_module.setStyleSheet("font-size:22px;font-weight:900;color:#c000ff;")
        self.boot_log=QLabel(); self.boot_log.setStyleSheet("font-family:Consolas;font-size:12px;color:#9ea9c0;")
        self.progress=QProgressBar(); self.progress.setRange(0,100); self.progress.setFormat("SYSTEM INITIALIZATION  %p%")
        right.addWidget(badge); right.addSpacing(16); right.addWidget(self.current_module); right.addWidget(self.boot_log,1); right.addWidget(self.progress); lay.addLayout(right,1)
        self.stack.addWidget(boot)
        login=QWidget(); ll=QHBoxLayout(login); ll.setContentsMargins(70,58,70,58); logo2=QSvgWidget(str(LOGO_PATH)); logo2.setFixedSize(280,280); ll.addWidget(logo2)
        form=QVBoxLayout(); title=QLabel("OPERATOR ACCESS"); title.setStyleSheet("font-size:30px;font-weight:950;color:#f4f1ff;")
        sub=QLabel("LOCAL SESSION // AUTHORIZED ENVIRONMENT"); sub.setStyleSheet("color:#00e5ff;font-size:10px;font-weight:800;letter-spacing:2px;")
        self.operator=QLineEdit("TYLER"); self.operator.setPlaceholderText("Operator name")
        clear=QLabel("CLEARANCE  // LEVEL 3\nCORE       // ONLINE\nIDENTITY   // VERIFIED"); clear.setStyleSheet("font-family:Consolas;color:#aab4c7;")
        enter=QPushButton("ENTER BLACKTERM"); enter.clicked.connect(self.accept_login)
        form.addStretch(); form.addWidget(title); form.addWidget(sub); form.addSpacing(30); form.addWidget(QLabel("OPERATOR")); form.addWidget(self.operator); form.addSpacing(18); form.addWidget(clear); form.addStretch(); form.addWidget(enter); ll.addLayout(form,1); self.stack.addWidget(login)
        self.steps=[("CORE SYSTEMS","Kernel services initialized"),("MEMORY","Secure workspace allocated"),("NETWORK","Network intelligence online"),("RECON","Recon engines armed"),("INTELLIGENCE","Threat context synchronized"),("AI ANALYST","Analyst context loaded"),("GRAPH ENGINE","Relationship renderer online"),("AUDIO SYSTEM","Sound identity initialized"),("UI/UX","Visual identity loaded"),("BLACKTERM OS","Platform online")]
        self.step_index=0; self.timer=QTimer(self); self.timer.timeout.connect(self.advance); self.timer.start(205); QTimer.singleShot(120,self.sound.play)
        QTimer.singleShot(120,lambda:self.sound.play("startup"))
    def advance(self):
        if self.step_index < len(self.steps):
            module,line=self.steps[self.step_index]; self.current_module.setText(module); self.boot_log.setText(self.boot_log.text()+f"[✓] {line}\n"); self.progress.setValue(int((self.step_index+1)/len(self.steps)*100)); self.step_index+=1; return
        self.timer.stop(); QTimer.singleShot(180,self._fade_to_login)
    def _fade_to_login(self):
        a=QPropertyAnimation(self,b"windowOpacity",self); a.setDuration(260); a.setStartValue(1.0); a.setEndValue(.12); a.setEasingCurve(QEasingCurve.InOutCubic); a.finished.connect(self._show_login); a.start(); self._fade_out=a
    def _show_login(self):
        self.stack.setCurrentIndex(1); a=QPropertyAnimation(self,b"windowOpacity",self); a.setDuration(360); a.setStartValue(.12); a.setEndValue(1.0); a.setEasingCurve(QEasingCurve.OutCubic); a.start(); self._fade_in=a
    def accept_login(self):
        self.sound.play("success"); name=self.operator.text().strip() or "OPERATOR"; self.accepted_operator.emit(name); self.accept()
