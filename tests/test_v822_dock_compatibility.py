from pathlib import Path


def test_dock_preserves_legacy_and_new_class_names():
    root = Path(__file__).resolve().parents[1]
    text = (root / "blackterm_recon/desktop/dock.py").read_text(encoding="utf-8")
    assert "class DockButton" in text
    assert "NavigationButton = DockButton" in text
    assert "OPERATOR DASHBOARD" in text
