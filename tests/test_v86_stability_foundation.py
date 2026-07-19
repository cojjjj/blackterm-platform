from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_animation_imports_and_timer_types_are_valid():
    text = read("blackterm_recon/desktop/animations.py")
    assert "QTimer, Qt, Signal" in text
    assert "Qt.TimerType.CoarseTimer" in text
    assert "Qt.TimerType.PreciseTimer" in text


def test_only_the_current_render_surface_is_integrated():
    main = read("blackterm_recon/desktop/main_window.py")
    assert "RenderSurface" in main
    assert "AmbientBackdrop" not in main
    assert "ParticleField" not in main


def test_render_surface_uses_one_painter_lifecycle():
    text = read("blackterm_recon/desktop/render_engine.py")
    assert text.count("QPainter()") == 1
    assert "if not painter.begin(self)" in text
    assert "finally:" in text
    assert "painter.end()" in text


def test_previous_runtime_fixes_remain():
    graph = read("blackterm_recon/desktop/investigation_graph.py")
    live = read("blackterm_recon/desktop/live_widgets.py")
    dock = read("blackterm_recon/desktop/dock.py")
    living = read("blackterm_recon/desktop/living_interface.py")

    assert "GraphicsItemAnimator" in graph
    assert "QPropertyAnimation(edge_item" not in graph
    assert "QTextCursor.MoveOperation.End" in live
    assert "class DockButton" in dock
    assert "QGraphicsOpacityEffect" not in living


def test_premium_features_remain_present():
    assert (ROOT / "blackterm_recon/desktop/premium_style.py").exists()
    assert (ROOT / "blackterm_recon/desktop/operator_dashboard_page.py").exists()
    assert (ROOT / "blackterm_recon/desktop/intelligence_page.py").exists()
