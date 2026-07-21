from blackterm_recon.attack_surface import build_attack_surface
from blackterm_recon.models import PortResult, ScanResult


def make_result(ports):
    return ScanResult(
        target="lab.local",
        ip="127.0.0.1",
        hostname="lab.local",
        ports=ports,
        started_at="2026-01-01T00:00:00+00:00",
        finished_at="2026-01-01T00:00:01+00:00",
        duration_seconds=1.0,
        operation_id="BT-TEST",
        profile="standard",
    )


def test_attack_surface_detects_services_and_technology():
    result = make_result([
        PortResult(22, "open", "ssh", banner="OpenSSH_9.6"),
        PortResult(80, "open", "http", banner="Apache/2.4.58"),
    ])
    surface = build_attack_surface(result)
    assert surface.open_ports == [22, 80]
    assert surface.services == ["http", "ssh"]
    assert "OpenSSH" in surface.technologies
    assert "Apache" in surface.technologies
    assert any(item.title == "Web application surface detected" for item in surface.findings)


def test_attack_surface_flags_high_risk_service():
    result = make_result([PortResult(23, "open", "telnet")])
    surface = build_attack_surface(result)
    assert surface.risk_level in {"MEDIUM", "HIGH", "CRITICAL"}
    assert any(item.severity == "high" for item in surface.findings)
    assert surface.attack_surface_score < 100


def test_attack_surface_handles_no_open_ports():
    result = make_result([PortResult(443, "closed", "https")])
    surface = build_attack_surface(result)
    assert surface.risk_level == "LOW"
    assert surface.attack_surface_score == 100
    assert surface.severity_counts["info"] == 1
