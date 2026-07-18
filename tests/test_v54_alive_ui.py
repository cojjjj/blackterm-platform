from pathlib import Path


def test_alive_ui_files_use_safe_unicode_and_qt_colors():
    root = Path(__file__).resolve().parents[1]
    mission = (root / "blackterm_recon/desktop/pages/mission_control.py").read_text(encoding="utf-8")
    assert "QBrush(QColor(color))" in mission
    assert "\\u2713" in mission
    assert "ThreatMeter" in mission
    assert "AI ANALYST" in mission


def test_widgets_include_animated_components():
    root = Path(__file__).resolve().parents[1]
    widgets = (root / "blackterm_recon/desktop/widgets.py").read_text(encoding="utf-8")
    assert "class ThreatMeter" in widgets
    assert "class Sparkline" in widgets
    assert "_animation_timer" in widgets
