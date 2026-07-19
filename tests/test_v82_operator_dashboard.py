from blackterm_recon.operator_dashboard import build_operator_stats, greeting_for_hour


class Repo:
    def list_cases(self):
        return [
            {
                "id": 2,
                "name": "New Case",
                "status": "ACTIVE",
                "scan_count": 1,
                "created_at": "2026-07-18T20:00:00+00:00",
            },
            {
                "id": 1,
                "name": "Old Case",
                "status": "CLOSED",
                "scan_count": 1,
                "created_at": "2026-07-17T20:00:00+00:00",
            },
        ]

    def case_evidence(self, case_id):
        return [{"id": 1}] * case_id

    def case_timeline(self, case_id):
        return [{"created_at": "2026-07-18T20:00:00+00:00"}] * case_id


def test_greeting_ranges():
    assert greeting_for_hour(8) == "GOOD MORNING"
    assert greeting_for_hour(14) == "GOOD AFTERNOON"
    assert greeting_for_hour(20) == "GOOD EVENING"
    assert greeting_for_hour(2) == "LATE SHIFT ACTIVE"


def test_operator_stats_aggregates_cases_and_resume_target():
    stats = build_operator_stats(Repo(), "Tyler")
    assert stats.operator == "TYLER"
    assert stats.total_cases == 2
    assert stats.active_cases == 1
    assert stats.evidence_items == 3
    assert stats.timeline_events == 3
    assert stats.last_case_id == 2
