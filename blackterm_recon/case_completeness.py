from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence


@dataclass(frozen=True, slots=True)
class CompletenessCheck:
    key: str
    label: str
    weight: int
    complete: bool
    detail: str


@dataclass(frozen=True, slots=True)
class CaseCompleteness:
    score: int
    level: str
    checks: tuple[CompletenessCheck, ...]

    @property
    def collected(self) -> tuple[CompletenessCheck, ...]:
        return tuple(check for check in self.checks if check.complete)

    @property
    def missing(self) -> tuple[CompletenessCheck, ...]:
        return tuple(check for check in self.checks if not check.complete)


def _text_blob(items: Iterable[Mapping], fields: Sequence[str]) -> str:
    values: list[str] = []
    for item in items:
        for field in fields:
            value = item.get(field)
            if value:
                values.append(str(value).lower())
    return "\n".join(values)


def assess_case_completeness(
    case: Mapping,
    scans: Sequence[Mapping],
    notes: Sequence[Mapping],
    evidence: Sequence[Mapping],
    timeline: Sequence[Mapping],
) -> CaseCompleteness:
    """Calculate case readiness from evidence already stored by BLACKTERM.

    The score is intentionally deterministic and local. It measures investigation
    coverage, not target risk or vulnerability severity.
    """

    description = str(case.get("description") or "").strip()
    evidence_blob = _text_blob(
        evidence,
        ("evidence_type", "title", "source", "content", "file_path"),
    )
    timeline_blob = _text_blob(timeline, ("event_type", "title", "detail"))
    open_ports = sum(int(scan.get("open_ports") or 0) for scan in scans)

    def contains(*terms: str) -> bool:
        return any(term.lower() in evidence_blob for term in terms)

    checks = (
        CompletenessCheck("scope", "Scope documented", 10, bool(description), "Record the authorized scope and investigation objective."),
        CompletenessCheck("scan", "Recon scan attached", 15, bool(scans), "Attach at least one authorized scan."),
        CompletenessCheck("services", "Services discovered", 8, open_ports > 0, "Collect service and open-port evidence."),
        CompletenessCheck("timeline", "Timeline populated", 8, len(timeline) >= 3, "Capture at least three meaningful investigation events."),
        CompletenessCheck("notes", "Operator notes recorded", 7, bool(notes), "Add an operator observation or next step."),
        CompletenessCheck("evidence", "Evidence preserved", 10, bool(evidence), "Add or capture an evidence item with a SHA-256 record."),
        CompletenessCheck("technology", "Technology fingerprinting", 10, contains("technology", "fingerprint", "server header", "framework"), "Run technology fingerprinting against an authorized web service."),
        CompletenessCheck("dns", "DNS intelligence", 7, contains("dns", "a record", "mx record", "cname"), "Collect DNS records for the target."),
        CompletenessCheck("tls", "TLS / certificate analysis", 7, contains("tls", "ssl", "certificate", "x.509"), "Capture TLS and certificate evidence when HTTPS is present."),
        CompletenessCheck("whois", "WHOIS / ownership context", 5, contains("whois", "registrar", "registrant"), "Add WHOIS or ownership context."),
        CompletenessCheck("screenshot", "Visual evidence captured", 6, contains("screenshot", "workspace capture", ".png", ".jpg", ".jpeg"), "Capture a workspace or target screenshot."),
        CompletenessCheck("correlation", "Intelligence correlation", 4, contains("correlation") or "correlation" in timeline_blob, "Run intelligence correlation."),
        CompletenessCheck("ai", "AI investigation summary", 3, contains("ai investigation", "blackterm ai", "ai analysis") or "ai investigation" in timeline_blob, "Generate an AI investigation summary."),
    )

    score = max(0, min(100, sum(check.weight for check in checks if check.complete)))
    if score >= 85:
        level = "MISSION READY"
    elif score >= 65:
        level = "WELL DEVELOPED"
    elif score >= 40:
        level = "IN PROGRESS"
    else:
        level = "EARLY STAGE"

    return CaseCompleteness(score=score, level=level, checks=checks)
