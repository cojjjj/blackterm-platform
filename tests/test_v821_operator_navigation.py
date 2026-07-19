from blackterm_recon.desktop.dock import NAV_ICONS


def test_navigation_contains_readable_operator_destination():
    assert "OPERATOR DASHBOARD" in NAV_ICONS
    assert "MISSION CONTROL" in NAV_ICONS
    assert "CASES" in NAV_ICONS


def test_every_primary_destination_has_a_nonempty_icon():
    assert all(str(value).strip() for value in NAV_ICONS.values())
