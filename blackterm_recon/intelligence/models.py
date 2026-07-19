from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True, slots=True)
class IntelligenceFinding:
    title: str
    detail: str
    severity: str = "INFO"
    risk: int = 0
    confidence: int = 70
    node_kind: str = "FINDING"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class IntelligenceEvidence:
    evidence_type: str
    title: str
    source: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class IntelligenceRelationship:
    source: str
    target: str
    relationship: str
    confidence: int = 75


@dataclass(frozen=True, slots=True)
class IntelligenceModuleResult:
    module: str
    status: str
    summary: str
    findings: tuple[IntelligenceFinding, ...] = ()
    evidence: tuple[IntelligenceEvidence, ...] = ()
    relationships: tuple[IntelligenceRelationship, ...] = ()
    risk: int = 0
    confidence: int = 0
    duration_ms: int = 0
    error: str = ""

    @property
    def successful(self) -> bool:
        return self.status == "success"


@dataclass(frozen=True, slots=True)
class IntelligenceRunResult:
    target: str
    normalized_target: str
    started_at: str
    completed_at: str
    modules: tuple[IntelligenceModuleResult, ...]
    risk_score: int
    confidence: int
    level: str
    summary: str

    @property
    def evidence_count(self) -> int:
        return sum(len(item.evidence) for item in self.modules)

    @property
    def finding_count(self) -> int:
        return sum(len(item.findings) for item in self.modules)

    def to_text(self) -> str:
        module_lines = []
        for item in self.modules:
            icon = "OK" if item.successful else "SKIP" if item.status == "skipped" else "ERROR"
            module_lines.append(
                f"[{icon}] {item.module.upper():<14} "
                f"risk={item.risk:<3} confidence={item.confidence:<3} {item.summary}"
            )
        findings = [
            f"- [{finding.severity}] {finding.title}: {finding.detail}"
            for module in self.modules
            for finding in module.findings
        ]
        return (
            "BLACKTERM INTELLIGENCE ENGINE\n\n"
            f"TARGET: {self.normalized_target}\n"
            f"PRIORITY: {self.level}\n"
            f"RISK SCORE: {self.risk_score}/100\n"
            f"CONFIDENCE: {self.confidence}%\n"
            f"EVIDENCE: {self.evidence_count}\n"
            f"FINDINGS: {self.finding_count}\n\n"
            f"SUMMARY\n{self.summary}\n\n"
            "MODULE PIPELINE\n"
            + "\n".join(module_lines)
            + "\n\nFINDINGS\n"
            + ("\n".join(findings) if findings else "- No high-signal finding was produced.")
            + "\n\nAuthorized-use intelligence only. Validate findings before operational action."
        )
