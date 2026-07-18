from blackterm_recon.database import ScanRepository
from blackterm_recon.models import PortResult, ScanResult


def test_case_creation_and_attachment(tmp_path):
    repo = ScanRepository(str(tmp_path / "history.db"))
    result = ScanResult(
        target="127.0.0.1",
        ip="127.0.0.1",
        hostname="localhost",
        started_at="a",
        finished_at="b",
        duration_seconds=0.1,
        ports=[PortResult(port=80, state="open", service="http")],
    )
    scan_id = repo.save(result)
    case_id = repo.create_case("Lab", "Authorized local lab")
    repo.attach_scan_to_case(case_id, scan_id)
    assert repo.list_cases()[0]["scan_count"] == 1
    assert repo.case_scans(case_id)[0]["id"] == scan_id


def test_scan_events(tmp_path):
    repo = ScanRepository(str(tmp_path / "history.db"))
    result = ScanResult(
        target="127.0.0.1",
        ip="127.0.0.1",
        hostname=None,
        started_at="a",
        finished_at="b",
        duration_seconds=0.1,
        ports=[],
    )
    scan_id = repo.save(result)
    repo.save_events(scan_id, [("now", "START", "Started")])
    assert repo.get_events(scan_id)[0]["event_type"] == "START"
