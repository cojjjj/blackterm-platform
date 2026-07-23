from pathlib import Path
from types import SimpleNamespace

from blackterm_recon.autonomous_workflow import (
    AutonomousWorkflowEngine,
    AutonomousWorkflowOptions,
)
from blackterm_recon.database import ScanRepository


def test_autonomous_workflow_creates_review_case_without_optional_stages(tmp_path):
    repository = ScanRepository(str(tmp_path / "workflow.db"))
    engine = SimpleNamespace(repository=repository, config=SimpleNamespace())
    result = AutonomousWorkflowEngine(engine).run(
        AutonomousWorkflowOptions(
            operation_name="Test workflow",
            target="example.com",
            run_recon=False,
            run_osint=False,
            run_threat_intelligence=False,
            run_ai_correlation=False,
            generate_report=False,
        )
    )
    assert result.status == "complete"
    case = next(item for item in repository.list_cases() if item["id"] == result.case_id)
    assert case["status"] == "REVIEW"
    timeline = repository.case_timeline(result.case_id)
    assert any(item["title"] == "Autonomous workflow complete" for item in timeline)
