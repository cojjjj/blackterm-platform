from pathlib import Path


def test_premium_visual_modules_exist():
    root = Path(__file__).resolve().parents[1]
    assert (root / "blackterm_recon/desktop/premium_style.py").exists()
    assert (root / "blackterm_recon/desktop/render_engine.py").exists()


def test_main_window_uses_safe_premium_layers():
    root = Path(__file__).resolve().parents[1]
    text = (root / "blackterm_recon/desktop/main_window.py").read_text(
        encoding="utf-8"
    )
    assert "RenderSurface" in text
    assert "AmbientBackdrop" not in text
    assert "ParticleField" not in text
    assert "premium_stylesheet" in text
    assert "self.fade_controller.fade_in" in text
    assert "QPropertyAnimation(page" not in text
    assert text.count("def resizeEvent") == 1


def test_intelligence_page_has_named_premium_sections():
    root = Path(__file__).resolve().parents[1]
    text = (root / "blackterm_recon/desktop/intelligence_page.py").read_text(
        encoding="utf-8"
    )
    for object_name in (
        "intelligenceLaunch",
        "intelligenceTelemetry",
        "intelligencePipeline",
        "intelligenceAnalysis",
        "liveReady",
        "liveActive",
        "liveComplete",
    ):
        assert object_name in text


def test_animation_stability_contracts_remain():
    root = Path(__file__).resolve().parents[1]
    graph = (root / "blackterm_recon/desktop/investigation_graph.py").read_text(
        encoding="utf-8"
    )
    live = (root / "blackterm_recon/desktop/live_widgets.py").read_text(
        encoding="utf-8"
    )
    dock = (root / "blackterm_recon/desktop/dock.py").read_text(
        encoding="utf-8"
    )
    animations = (root / "blackterm_recon/desktop/animations.py").read_text(
        encoding="utf-8"
    )
    assert "GraphicsItemAnimator" in graph
    assert "QTextCursor.MoveOperation.End" in live
    assert "class DockButton" in dock
    assert "QGraphicsOpacityEffect" not in animations
