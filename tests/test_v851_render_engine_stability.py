from pathlib import Path


def test_single_render_surface_replaces_overlapping_layers():
    root = Path(__file__).resolve().parents[1]
    main = (root / "blackterm_recon/desktop/main_window.py").read_text(encoding="utf-8")
    assert "RenderSurface" in main
    assert "AmbientBackdrop" not in main
    assert "ParticleField" not in main


def test_render_surface_has_one_explicit_painter_lifecycle():
    root = Path(__file__).resolve().parents[1]
    text = (root / "blackterm_recon/desktop/render_engine.py").read_text(encoding="utf-8")
    assert text.count("QPainter()") == 1
    assert "if not painter.begin(self)" in text
    assert "finally:" in text
    assert "painter.end()" in text


def test_graphics_opacity_effects_are_not_used_for_widget_motion():
    root = Path(__file__).resolve().parents[1]
    animations = (root / "blackterm_recon/desktop/animations.py").read_text(encoding="utf-8")
    living = (root / "blackterm_recon/desktop/living_interface.py").read_text(encoding="utf-8")
    assert "QGraphicsOpacityEffect" not in animations
    assert "QGraphicsOpacityEffect" not in living
    assert "PalettePulse" in animations


def test_previous_compatibility_fixes_remain():
    root = Path(__file__).resolve().parents[1]
    graph = (root / "blackterm_recon/desktop/investigation_graph.py").read_text(encoding="utf-8")
    live = (root / "blackterm_recon/desktop/live_widgets.py").read_text(encoding="utf-8")
    dock = (root / "blackterm_recon/desktop/dock.py").read_text(encoding="utf-8")
    assert "GraphicsItemAnimator" in graph
    assert "QTextCursor.MoveOperation.End" in live
    assert "class DockButton" in dock
