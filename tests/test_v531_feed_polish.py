from pathlib import Path


def test_mission_control_uses_qbrush_and_ascii_safe_source():
    path = Path("blackterm_recon/desktop/pages/mission_control.py")
    source = path.read_text(encoding="utf-8")
    source.encode("ascii")
    assert "QBrush(QColor(color))" in source
    assert source.startswith("from __future__ import annotations")


def test_event_feed_source_is_ascii_safe():
    path = Path("blackterm_recon/desktop/event_feed.py")
    source = path.read_text(encoding="utf-8")
    source.encode("ascii")
    assert "\\u2713" in source
    assert "platform_event" in source
