from blackterm_recon.operations import new_operation_id
from blackterm_recon.profiles import SCAN_PROFILES, get_profile


def test_builtin_profiles_have_resolvable_ports():
    assert {"quick", "standard", "full", "custom"}.issubset(SCAN_PROFILES)
    for profile in SCAN_PROFILES.values():
        ports = profile.resolved_ports()
        assert ports
        assert all(1 <= port <= 65535 for port in ports)


def test_operation_id_is_human_readable_and_unique():
    first = new_operation_id()
    second = new_operation_id()
    assert first.startswith("BT-")
    assert first != second


def test_unknown_profile_is_rejected():
    try:
        get_profile("impossible")
    except ValueError as exc:
        assert "Unknown scan profile" in str(exc)
    else:
        raise AssertionError("Expected ValueError")
