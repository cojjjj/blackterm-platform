from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True, slots=True)
class ThreatFinding:
    title: str
    detail: str
    severity: str = "INFO"
    score: int = 0
    confidence: int = 70
    source: str = "BLACKTERM"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ThreatEvidence:
    evidence_type: str
    title: str
    source: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ProviderResult:
    provider: str
    status: str
    summary: str
    findings: tuple[ThreatFinding, ...] = ()
    evidence: tuple[ThreatEvidence, ...] = ()
    score: int = 0
    confidence: int = 0
    duration_ms: int = 0
    error: str = ""

    @property
    def successful(self) -> bool:
        return self.status == "success"


@dataclass(frozen=True, slots=True)
class ThreatIntelligenceResult:
    target: str
    indicator: str
    indicator_type: str
    started_at: str
    completed_at: str
    providers: tuple[ProviderResult, ...]
    threat_score: int
    confidence: int
    level: str
    verdict: str
    summary: str
    ioc_matches: int = 0
    cve_matches: int = 0
    context: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def findings(self) -> tuple[ThreatFinding, ...]:
        return tuple(f for p in self.providers for f in p.findings)

    @property
    def evidence(self) -> tuple[ThreatEvidence, ...]:
        return tuple(e for p in self.providers for e in p.evidence)

    def to_text(self) -> str:
        provider_lines = []
        for item in self.providers:
            icon = "OK" if item.status == "success" else "SKIP" if item.status == "skipped" else "ERROR"
            provider_lines.append(
                f"[{icon}] {item.provider.upper():<16} score={item.score:<3} confidence={item.confidence:<3} {item.summary}"
            )
        finding_lines = [
            f"- [{f.severity}] {f.title}: {f.detail} (source: {f.source})"
            for f in self.findings
        ]
        return (
            "BLACKTERM THREAT INTELLIGENCE CENTER\n\n"
            f"INDICATOR: {self.indicator}\n"
            f"TYPE: {self.indicator_type.upper()}\n"
            f"VERDICT: {self.verdict}\n"
            f"THREAT SCORE: {self.threat_score}/100\n"
            f"CONFIDENCE: {self.confidence}%\n"
            f"IOC MATCHES: {self.ioc_matches}\n"
            f"CVE MATCHES: {self.cve_matches}\n\n"
            f"ASSESSMENT\n{self.summary}\n\n"
            "PROVIDER PIPELINE\n" + "\n".join(provider_lines) +
            "\n\nFINDINGS\n" + ("\n".join(finding_lines) if finding_lines else "- No high-signal threat finding was produced.") +
            "\n\nThreat intelligence is advisory. Validate findings and respect provider terms and authorization requirements."
        )
