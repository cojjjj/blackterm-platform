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
