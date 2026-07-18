from types import SimpleNamespace

from blackterm_recon.investigation_engine import assess_result


def result(*ports):
    items = [SimpleNamespace(port=p, service=s, latency_ms=1.5, banner="") for p, s in ports]
    return SimpleNamespace(target="192.0.2.10", open_ports=items)


def test_empty_result_is_low_context():
    assessment = assess_result(result())
    assert assessment.level == "LOW"
    assert assessment.score < 25
    assert "No open TCP services" in assessment.summary


def test_sensitive_services_raise_context():
    assessment = assess_result(result((23, "telnet"), (445, "microsoft-ds"), (3389, "ms-wbt-server")))
    assert assessment.score >= 75
    assert assessment.level == "CRITICAL"
    assert "Telnet" in assessment.summary
    assert any("SMB" in item for item in assessment.recommendations)


def test_regular_services_generate_recommendations():
    assessment = assess_result(result((22, "ssh"), (80, "http")))
    assert assessment.level in {"LOW", "GUARDED"}
    assert len(assessment.recommendations) >= 2
