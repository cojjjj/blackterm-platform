from __future__ import annotations
from pathlib import Path
from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QUrl
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QGraphicsOpacityEffect, QWidget

ASSET_DIR = Path(__file__).resolve().parent / "assets"
LOGO_PATH = ASSET_DIR / "blackterm-logo.svg"
SOUND_DIR = ASSET_DIR / "sounds"

PALETTE = {
    "void": "#050713", "surface": "#090d1b", "panel": "#0d1224",
    "panel_alt": "#131a31", "purple": "#a82be2", "violet": "#c000ff",
    "cyan": "#00e5ff", "mint": "#00ffc3", "text": "#f4f1ff",
    "muted": "#8994ad", "border": "#2d2850", "danger": "#ff315f",
    "warning": "#ffb020", "success": "#00ef9b",
}

def app_icon() -> QIcon:
    return QIcon(str(LOGO_PATH))

def fade_in(widget: QWidget, duration: int = 220):
    effect = QGraphicsOpacityEffect(widget)
    widget.setGraphicsEffect(effect)
    animation = QPropertyAnimation(effect, b"opacity", widget)
    animation.setDuration(duration)
    animation.setStartValue(0.0)
    animation.setEndValue(1.0)
    animation.setEasingCurve(QEasingCurve.OutCubic)
    animation.finished.connect(lambda: widget.setGraphicsEffect(None))
    animation.start()
    widget._blackterm_fade_animation = animation

class SoundIdentity:
    def __init__(self, parent=None):
        self.enabled = True
        self._effects = {}
        try:
            from PySide6.QtMultimedia import QSoundEffect
            for name in ("startup", "navigate", "success", "alert"):
                effect = QSoundEffect(parent)
                effect.setSource(QUrl.fromLocalFile(str(SOUND_DIR / f"{name}.wav")))
                effect.setVolume(0.28 if name == "startup" else 0.18)
                self._effects[name] = effect
        except Exception:
            self.enabled = False
    def play(self, name: str = "startup"):
        if self.enabled and name in self._effects:
            self._effects[name].play()
