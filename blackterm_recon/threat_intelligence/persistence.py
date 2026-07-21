from __future__ import annotations
from typing import Any
from .models import ThreatIntelligenceResult


def persist_threat_run(repository: Any, result: ThreatIntelligenceResult, *, case_id: int | None = None) -> int:
    if case_id is None:
        case_id = int(repository.create_case(
            f"THREAT-{result.indicator}",
            f"Threat intelligence assessment for {result.indicator}. Authorized-use reputation enrichment."
        ))
    repository.add_case_timeline(case_id, "THREAT", "Threat intelligence started", f"Indicator: {result.indicator}")
    for provider in result.providers:
        repository.add_case_timeline(case_id, "THREAT", f"{provider.provider.upper()} {provider.status}", provider.summary)
        for evidence in provider.evidence:
            repository.add_case_evidence(case_id, evidence.evidence_type, evidence.title, evidence.source, evidence.content)
    repository.add_case_evidence(case_id, "THREAT_INTELLIGENCE", "BLACKTERM threat assessment", result.indicator, result.to_text())
    repository.add_case_timeline(case_id, "THREAT", "Threat intelligence completed", f"{result.level} / {result.threat_score}/100 / {result.confidence}% confidence")
    return case_id
