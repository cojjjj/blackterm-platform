from pathlib import Path

from blackterm_recon.desktop.animations import GraphicsItemAnimator, WidgetAnimator


def test_central_animation_classes_exist():
    assert GraphicsItemAnimator is not None
    assert WidgetAnimator is not None


def test_qtextcursor_uses_pyside6_move_operation_enum():
    root = Path(__file__).resolve().parents[1]
    text = (root / "blackterm_recon/desktop/live_widgets.py").read_text(
        encoding="utf-8"
    )
    assert "QTextCursor.MoveOperation.End" in text
    assert "self.textCursor().End" not in text


def test_graph_never_property_animates_plain_edge_item():
    root = Path(__file__).resolve().parents[1]
    text = (root / "blackterm_recon/desktop/investigation_graph.py").read_text(
        encoding="utf-8"
    )
    assert "GraphicsItemAnimator" in text
    assert 'QPropertyAnimation(edge_item' not in text
    assert 'QPropertyAnimation(item, b"opacity"' not in text


def test_legacy_navigation_contract_remains():
    root = Path(__file__).resolve().parents[1]
    text = (root / "blackterm_recon/desktop/dock.py").read_text(encoding="utf-8")
    assert "class DockButton" in text
    assert "NavigationButton = DockButton" in text
