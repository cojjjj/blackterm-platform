from __future__ import annotations

from typing import Any

from .models import IntelligenceRunResult


def persist_intelligence_run(
    repository: Any,
    result: IntelligenceRunResult,
    *,
    case_id: int | None = None,
) -> int:
    """Persist a run into BLACKTERM's existing case/evidence/timeline model."""
    if case_id is None:
        name = f"INTEL-{result.normalized_target}"
        description = (
            f"Autonomous intelligence investigation for {result.normalized_target}. "
            "Authorized-use passive collection."
        )
        case_id = int(repository.create_case(name, description))

    repository.add_case_timeline(
        case_id,
        "INTEL",
        "Intelligence pipeline started",
        f"Target: {result.normalized_target}",
    )

    for module in result.modules:
        for evidence in module.evidence:
            repository.add_case_evidence(
                case_id,
                evidence.evidence_type,
                evidence.title,
                evidence.source,
                evidence.content,
            )
        repository.add_case_timeline(
            case_id,
            "INTEL",
            f"{module.module.upper()} {module.status}",
            module.summary,
        )

    repository.add_case_evidence(
        case_id,
        "INTELLIGENCE",
        "BLACKTERM Intelligence Engine summary",
        result.normalized_target,
        result.to_text(),
    )
    repository.add_case_timeline(
        case_id,
        "INTEL",
        "Intelligence pipeline completed",
        f"{result.level} priority / {result.confidence}% confidence / "
        f"{result.evidence_count} evidence item(s)",
    )
    return case_id
