from blackterm_recon.intelligence.engine import IntelligenceEngine
from blackterm_recon.intelligence.models import IntelligenceModuleResult
from blackterm_recon.intelligence.modules import normalize_target


def test_normalize_target_handles_urls_and_domains():
    assert normalize_target("https://example.com/path")[0] == "example.com"
    assert normalize_target("example.com")[0] == "example.com"


def test_engine_aggregates_module_results(monkeypatch):
    import blackterm_recon.intelligence.engine as engine_module

    def good(target, **kwargs):
        return IntelligenceModuleResult(
            module="dns", status="success", summary="done", risk=12, confidence=90
        )

    monkeypatch.setattr(engine_module, "BUILTIN_MODULES", (("dns", good),))
    result = IntelligenceEngine(max_workers=1).run("example.com", enabled_modules=("dns",))
    assert result.risk_score == 12
    assert result.confidence >= 90
    assert result.modules[0].successful
