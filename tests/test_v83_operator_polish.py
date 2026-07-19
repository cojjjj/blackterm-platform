from pathlib import Path


def test_operator_dashboard_contains_polish_components():
    root = Path(__file__).resolve().parents[1]
    text = (root / "blackterm_recon/desktop/operator_dashboard_page.py").read_text(
        encoding="utf-8"
    )
    assert "class MiniSparkline" in text
    assert "class MetricCard" in text
    assert "class StatusPill" in text
    assert "OPERATIONAL LOAD" in text
    assert "START LIVE INVESTIGATION" in text


def test_dock_still_preserves_legacy_class_contract():
    root = Path(__file__).resolve().parents[1]
    text = (root / "blackterm_recon/desktop/dock.py").read_text(encoding="utf-8")
    assert "class DockButton" in text
    assert "NavigationButton = DockButton" in text
