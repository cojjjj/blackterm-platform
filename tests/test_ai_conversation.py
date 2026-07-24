from blackterm_recon.assistant_engine import build_case_analyst_brief, answer_case_question
from blackterm_recon.database import ScanRepository
from blackterm_recon.models import PortResult, ScanResult


def scan(ports, finished):
    return ScanResult(
        target="example.local", ip="127.0.0.1", hostname="example.local",
        started_at="2026-01-01T00:00:00+00:00", finished_at=finished,
        duration_seconds=0.2,
        ports=[PortResult(port=p, state="open", service="microsoft-ds" if p == 445 else "http") for p in ports],
    )


def test_case_brief_and_memory(tmp_path):
    repo = ScanRepository(str(tmp_path / "db.sqlite"))
    older = repo.save(scan([80], "2026-01-01T00:01:00+00:00"))
    newer = repo.save(scan([80, 445], "2026-01-02T00:01:00+00:00"))
    case_id = repo.create_case("Operation Test", "Authorized")
    repo.attach_scan_to_case(case_id, newer)
    repo.add_case_evidence(case_id, "OBSERVATION", "SMB observed", "scan", "TCP/445")
    brief = build_case_analyst_brief(repo, case_id)
    assert brief.target == "example.local"
    assert any("TCP/445" in item for item in brief.memory)
    assert any("SMB" in item for item in brief.inferences)
    assert brief.confidence > 0


def test_case_conversation(tmp_path):
    repo = ScanRepository(str(tmp_path / "db.sqlite"))
    sid = repo.save(scan([445], "2026-01-01T00:01:00+00:00"))
    case_id = repo.create_case("Operation Test")
    repo.attach_scan_to_case(case_id, sid)
    assert answer_case_question("what should I do next", repo, case_id).intent == "next"
    assert "SMB" in answer_case_question("explain SMB", repo, case_id).body


def test_conversation_references_and_suggestions(tmp_path):
    repo = ScanRepository(str(tmp_path / "db.sqlite"))
    sid = repo.save(scan([80, 445], "2026-01-01T00:01:00+00:00"))
    case_id = repo.create_case("Operation Chat")
    repo.attach_scan_to_case(case_id, sid)
    repo.add_case_evidence(case_id, "OBSERVATION", "SMB banner", "scan", "microsoft-ds")
    reply = answer_case_question("why is this risky", repo, case_id)
    assert reply.evidence_refs
    assert any("scan" in item.lower() for item in reply.evidence_refs)
    assert "What should I do next?" in reply.suggestions


def test_port_explanation_and_quality(tmp_path):
    repo = ScanRepository(str(tmp_path / "db.sqlite"))
    sid = repo.save(scan([80, 445], "2026-01-01T00:01:00+00:00"))
    case_id = repo.create_case("Operation Quality")
    repo.attach_scan_to_case(case_id, sid)
    ports = answer_case_question("explain every open port", repo, case_id)
    quality = answer_case_question("how complete is this investigation", repo, case_id)
    assert "TCP/80" in ports.body and "TCP/445" in ports.body
    assert quality.intent == "quality"
    assert "INVESTIGATION QUALITY" in quality.body
