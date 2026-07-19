from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True, slots=True)
class OperatorStats:
    operator: str
    greeting: str
    total_cases: int
    active_cases: int
    high_priority_cases: int
    evidence_items: int
    relationships: int
    timeline_events: int
    today_activity: int
    last_case_id: int | None
    last_case_name: str
    last_case_status: str
    last_case_created: str
    recent_cases: tuple[dict[str, Any], ...]


def _utc_date_prefix() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def greeting_for_hour(hour: int) -> str:
    if 5 <= hour < 12:
        return "GOOD MORNING"
    if 12 <= hour < 18:
        return "GOOD AFTERNOON"
    if 18 <= hour < 23:
        return "GOOD EVENING"
    return "LATE SHIFT ACTIVE"


def _safe_list(callable_obj, *args):
    try:
        value = callable_obj(*args)
        return list(value or [])
    except Exception:
        return []


def build_operator_stats(repository, operator: str = "TYLER") -> OperatorStats:
    cases = _safe_list(repository.list_cases)
    today = _utc_date_prefix()
    total_evidence = 0
    total_timeline = 0
    total_relationships = 0
    today_activity = 0
    high_priority = 0

    def case_sort_key(item):
        return str(item.get("created_at", ""))

    ordered = sorted(cases, key=case_sort_key, reverse=True)

    for case in ordered:
        case_id = int(case.get("id", 0) or 0)
        evidence = _safe_list(repository.case_evidence, case_id)
        timeline = _safe_list(repository.case_timeline, case_id)
        total_evidence += len(evidence)
        total_timeline += len(timeline)
        today_activity += sum(
            1 for event in timeline
            if str(event.get("created_at", "")).startswith(today)
        )

        # Relationship totals are estimated from the graph model if correlation is available.
        try:
            from .correlation_engine import correlate_case
            report = correlate_case(repository, case_id)
            total_relationships += len(report.edges)
            if str(report.level).upper() in {"HIGH", "CRITICAL"}:
                high_priority += 1
        except Exception:
            pass

    active = sum(
        1 for case in cases
        if str(case.get("status", "")).upper() in {"OPEN", "ACTIVE", "REVIEW"}
    )
    last = ordered[0] if ordered else {}
    now_hour = datetime.now().hour

    return OperatorStats(
        operator=(operator or "OPERATOR").strip().upper(),
        greeting=greeting_for_hour(now_hour),
        total_cases=len(cases),
        active_cases=active,
        high_priority_cases=high_priority,
        evidence_items=total_evidence,
        relationships=total_relationships,
        timeline_events=total_timeline,
        today_activity=today_activity,
        last_case_id=int(last["id"]) if last.get("id") is not None else None,
        last_case_name=str(last.get("name", "No investigation yet")),
        last_case_status=str(last.get("status", "READY")),
        last_case_created=str(last.get("created_at", "")),
        recent_cases=tuple(ordered[:8]),
    )
