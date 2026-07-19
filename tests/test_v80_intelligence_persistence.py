from blackterm_recon.intelligence.models import IntelligenceModuleResult, IntelligenceRunResult
from blackterm_recon.intelligence.persistence import persist_intelligence_run


class Repo:
    def __init__(self):
        self.evidence = []
        self.timeline = []

    def create_case(self, name, description):
        return 8

    def add_case_evidence(self, *args):
        self.evidence.append(args)

    def add_case_timeline(self, *args):
        self.timeline.append(args)


def test_persistence_creates_case_summary_and_timeline():
    result = IntelligenceRunResult(
        target="example.com", normalized_target="example.com",
        started_at="a", completed_at="b",
        modules=(IntelligenceModuleResult("dns", "success", "resolved"),),
        risk_score=0, confidence=90, level="LOW", summary="complete",
    )
    repo = Repo()
    case_id = persist_intelligence_run(repo, result)
    assert case_id == 8
    assert repo.evidence
    assert len(repo.timeline) >= 3
