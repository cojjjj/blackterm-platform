from dataclasses import dataclass

from blackterm_recon.correlation_engine import correlate_case


@dataclass
class Port:
    port: int
    service: str


@dataclass
class Result:
    target: str
    ip: str
    open_ports: list[Port]


class Repository:
    def case_scans(self, case_id):
        return [
            {"id": 1, "target": "example.test", "ip": "192.0.2.10"},
            {"id": 2, "target": "example.test", "ip": "192.0.2.10"},
        ]

    def get(self, scan_id):
        return Result("example.test", "192.0.2.10", [Port(22, "ssh"), Port(445, "smb")])

    def case_evidence(self, case_id):
        return [
            {"id": 1, "evidence_type": "DNS", "title": "DNS record", "source": "example.test"},
            {"id": 2, "evidence_type": "SSL", "title": "TLS certificate", "source": "example.test"},
            {"id": 3, "evidence_type": "WHOIS", "title": "Registration", "source": "example.test"},
        ]

    def case_notes(self, case_id):
        return [{"note": "Validate SMB exposure"}]


def test_correlation_connects_multiple_sources():
    report = correlate_case(Repository(), 7)
    assert report.case_id == 7
    assert report.score >= 30
    assert report.confidence >= 70
    assert len(report.nodes) >= 8
    assert len(report.edges) >= 8
    assert any("Multiple evidence classes" in pattern for pattern in report.patterns)
    assert "INTELLIGENCE CORRELATION" in report.to_text()


def test_correlation_identifies_repeated_sensitive_service():
    report = correlate_case(Repository(), 7)
    assert any("Repeated service exposure" in pattern for pattern in report.patterns)
    assert any("SMB" in pattern for pattern in report.patterns)
