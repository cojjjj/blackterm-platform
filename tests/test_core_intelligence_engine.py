from pathlib import Path

from blackterm_recon.config import AppConfig
from blackterm_recon.database import ScanRepository
from blackterm_recon.intelligence import (
    IntelligenceEngine,
    IntelligenceModuleSpec,
    IntelligenceRegistry,
)
from blackterm_recon.intelligence.models import IntelligenceModuleResult
from blackterm_recon.models import PortResult, ScanResult


def sample_scan() -> ScanResult:
    return ScanResult(
        target="localhost",
        ip="127.0.0.1",
        hostname="localhost",
        started_at="a",
        finished_at="b",
        duration_seconds=0.1,
        operation_id="BT-TEST",
        profile="quick",
        attack_surface={
            "risk_score": 12,
            "technologies": ["Python HTTP Server"],
        },
        ports=[PortResult(8000, "open", "http", 1.2, "Server: SimpleHTTP/0.6 Python/3")],
    )


def test_run_for_scan_creates_normalized_intelligence_result():
    scan = sample_scan()
    result = IntelligenceEngine(max_workers=1).run_for_scan(scan)
    assert result.operation_id == "BT-TEST"
    assert result.context["source"] == "scan"
    assert result.evidence_count >= 2
    assert result.modules[0].module == "scan_context"
    assert any(item.relationships for item in result.modules)


def test_registry_resolves_dependencies_in_stages():
    def handler(target, **kwargs):
        return IntelligenceModuleResult("base", "success", "ok")

    registry = IntelligenceRegistry(
        (
            IntelligenceModuleSpec("base", handler),
            IntelligenceModuleSpec("child", handler, dependencies=("base",)),
        )
    )
    stages = registry.resolve(("child",))
    assert [[item.name for item in stage] for stage in stages] == [["base"], ["child"]]


def test_repository_persists_intelligence_json(tmp_path: Path):
    repository = ScanRepository(str(tmp_path / "recon.db"))
    scan = sample_scan()
    scan.intelligence = IntelligenceEngine(max_workers=1).run_for_scan(scan).to_dict()
    scan_id = repository.save(scan)
    loaded = repository.get(scan_id)
    assert loaded is not None
    assert loaded.intelligence["operation_id"] == "BT-TEST"
    assert loaded.intelligence["modules"][0]["module"] == "scan_context"
