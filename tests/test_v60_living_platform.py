from pathlib import Path


def test_v60_living_platform_components_exist():
    root = Path(__file__).resolve().parents[1]
    dock = (root / "blackterm_recon/desktop/dock.py").read_text(encoding="utf-8")
    feed = (root / "blackterm_recon/desktop/event_feed.py").read_text(encoding="utf-8")
    mission = (root / "blackterm_recon/desktop/pages/mission_control.py").read_text(encoding="utf-8")
    widgets = (root / "blackterm_recon/desktop/widgets.py").read_text(encoding="utf-8")
    startup = (root / "blackterm_recon/desktop/startup.py").read_text(encoding="utf-8")

    assert "class DockButton" in dock
    assert "Queued bottom-right toast" in feed
    assert "CASE / ACTIVITY TIMELINE" in mission
    assert "class TypingLabel" in widgets
    assert "LIVING DESKTOP SECURITY PLATFORM // v6.0" in startup


def test_future_imports_stay_first():
    root = Path(__file__).resolve().parents[1]
    for relative in [
        "blackterm_recon/desktop/dock.py",
        "blackterm_recon/desktop/event_feed.py",
        "blackterm_recon/desktop/startup.py",
        "blackterm_recon/desktop/pages/mission_control.py",
    ]:
        text = (root / relative).read_text(encoding="utf-8").lstrip("\ufeff\n")
        assert text.startswith("from __future__ import annotations")
