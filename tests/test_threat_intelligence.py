from blackterm_recon.threat_intelligence.engine import ThreatIntelligenceEngine, normalize_indicator
from blackterm_recon.threat_intelligence.models import ProviderResult, ThreatFinding


def test_normalize_indicator():
    assert normalize_indicator("https://Example.com/path") == ("example.com", "domain")
    assert normalize_indicator("1.1.1.1") == ("1.1.1.1", "ip")


def test_engine_aggregates_provider_results(monkeypatch):
    from blackterm_recon.threat_intelligence import engine as module
    monkeypatch.setattr(module, "PROVIDERS", {
        "one": lambda *a, **k: ProviderResult("one", "success", "hit", (ThreatFinding("match", "known", "HIGH", 70, 95, "one"),), score=70, confidence=95),
        "two": lambda *a, **k: ProviderResult("two", "success", "clean", score=0, confidence=80),
    })
    result = ThreatIntelligenceEngine().run("example.com", enabled_providers=("one", "two"))
    assert result.threat_score >= 50
    assert result.ioc_matches == 1
    assert result.verdict in {"SUSPICIOUS", "KNOWN OR STRONGLY SUSPECTED MALICIOUS"}
