from blackterm_recon.database import ScanRepository


def test_case_notes(tmp_path):
    repo = ScanRepository(str(tmp_path / "history.db"))
    case_id = repo.create_case("Office", "Authorized test")
    note_id = repo.add_case_note(case_id, "Initial observation")
    notes = repo.case_notes(case_id)
    assert note_id > 0
    assert notes[0]["note"] == "Initial observation"
