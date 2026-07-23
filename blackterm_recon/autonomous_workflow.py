from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Callable

from .case_reporting import write_case_report
from .correlation_engine import correlate_case
from .intelligence import IntelligenceEngine
from .investigation_engine import assess_result
from .profiles import get_profile
from .threat_intelligence import ThreatIntelligenceEngine


ProgressCallback = Callable[[str, int, str, dict], None]


@dataclass(frozen=True, slots=True)
class AutonomousWorkflowOptions:
    operation_name: str
    target: str
    profile: str = "standard"
    run_recon: bool = True
    run_osint: bool = True
    run_threat_intelligence: bool = True
    run_ai_correlation: bool = True
    generate_report: bool = True


@dataclass(frozen=True, slots=True)
class AutonomousWorkflowResult:
    case_id: int
    scan_id: int | None
    target: str
    status: str
    report_path: str = ""
    summary: str = ""


class AutonomousWorkflowEngine:
    """Runs a bounded, authorized investigation and persists every stage to one case."""

    STAGES = ("recon", "osint", "threat", "correlation", "report")

    def __init__(self, engine, event_bus=None):
        self.engine = engine
        self.event_bus = event_bus

    def _event(self, title: str, message: str, *, module: str, target: str,
               case_id: int | None = None, level_name: str = "INFO") -> None:
        if not self.event_bus:
            return
        from .events import EventLevel
        level = getattr(EventLevel, level_name, EventLevel.INFO)
        self.event_bus.emit(
            "autonomous", message, title=title, level=level, module=module,
            metadata={"target": target, "case_id": case_id, "workflow": "autonomous"},
        )

    def _progress(self, callback: ProgressCallback | None, stage: str, percent: int,
                  message: str, **metadata) -> None:
        if callback:
            callback(stage, max(0, min(100, int(percent))), message, metadata)

    def run(self, options: AutonomousWorkflowOptions,
            progress: ProgressCallback | None = None) -> AutonomousWorkflowResult:
        target = options.target.strip()
        if not target:
            raise ValueError("A target is required.")
        name = options.operation_name.strip() or f"AUTO-{datetime.now(timezone.utc):%Y%m%d-%H%M%S} // {target}"
        repository = self.engine.repository
        case_id = repository.create_case(
            name,
            f"Authorized autonomous BLACKTERM investigation for {target}.",
        )
        repository.update_case_status(case_id, "ACTIVE")
        repository.add_case_timeline(case_id, "AUTOMATION", "Autonomous workflow started", target)
        self._event("Investigation Started", f"Autonomous investigation started for {target}.",
                    module="workflow", target=target, case_id=case_id, level_name="SUCCESS")

        scan_id = None
        scan_result = None
        intelligence_result = None
        threat_result = None
        report_path = ""
        summaries: list[str] = []

        try:
            if options.run_recon:
                self._progress(progress, "recon", 5, "Reconnaissance initialized.", case_id=case_id)
                self._event("Recon Started", f"Authorized reconnaissance started for {target}.",
                            module="recon", target=target, case_id=case_id)
                profile = get_profile(options.profile)
                self.engine.config.timeout = profile.timeout
                self.engine.config.workers = profile.workers
                self.engine.config.banners = profile.banners
                ports = profile.resolved_ports()

                def scan_progress(done, total, item):
                    pct = int(done / max(1, total) * 100)
                    detail = f"TCP/{item.port} {item.state}"
                    self._progress(progress, "recon", pct, detail, case_id=case_id)

                scan_id, scan_result = self.engine.scan(target, ports, scan_progress, profile=profile.key)
                repository.attach_scan_to_case(case_id, scan_id)
                assessment = assess_result(scan_result)
                repository.add_case_evidence(
                    case_id, "RECON", f"Reconnaissance result #{scan_id}",
                    source="BLACKTERM Recon Engine",
                    content=json.dumps({
                        "scan_id": scan_id,
                        "target": target,
                        "operation_id": scan_result.operation_id,
                        "open_ports": [item.to_dict() for item in scan_result.open_ports],
                        "attack_surface": scan_result.attack_surface,
                        "assessment": assessment.to_text(),
                    }, indent=2),
                )
                summaries.append(assessment.summary)
                self._progress(progress, "recon", 100, "Reconnaissance complete.", case_id=case_id)
                self._event("Recon Complete", f"Recon completed with {len(scan_result.open_ports)} open port(s).",
                            module="recon", target=target, case_id=case_id, level_name="SUCCESS")

            if options.run_osint:
                self._progress(progress, "osint", 0, "Public-source enrichment initialized.", case_id=case_id)
                self._event("OSINT Started", f"Public-source enrichment started for {target}.",
                            module="osint", target=target, case_id=case_id)
                intelligence_result = IntelligenceEngine(
                    timeout=max(2.0, float(getattr(self.engine.config, "threat_timeout", 8.0))),
                    max_workers=max(1, min(8, int(getattr(self.engine.config, "workers", 4)))),
                ).run(
                    target,
                    scan_result=scan_result,
                    attack_surface=getattr(scan_result, "attack_surface", None),
                    progress=lambda module, pct, message, result: self._progress(
                        progress, "osint", pct, f"{module.upper()}: {message}", case_id=case_id
                    ),
                )
                repository.add_case_evidence(
                    case_id, "OSINT", "Autonomous OSINT intelligence package",
                    source="BLACKTERM Intelligence Engine",
                    content=json.dumps(intelligence_result.to_dict(), indent=2),
                )
                summaries.append(intelligence_result.summary)
                self._progress(progress, "osint", 100, "OSINT enrichment complete.", case_id=case_id)
                self._event("OSINT Complete", intelligence_result.summary, module="osint",
                            target=target, case_id=case_id, level_name="SUCCESS")

            if options.run_threat_intelligence:
                self._progress(progress, "threat", 0, "Threat-provider correlation initialized.", case_id=case_id)
                self._event("Threat Intelligence Started", f"Reputation analysis started for {target}.",
                            module="threat", target=target, case_id=case_id)
                threat_result = ThreatIntelligenceEngine(
                    timeout=float(getattr(self.engine.config, "threat_timeout", 8.0)),
                    virustotal_api_key=getattr(self.engine.config, "virustotal_api_key", ""),
                    abuseipdb_api_key=getattr(self.engine.config, "abuseipdb_api_key", ""),
                ).run(
                    target,
                    progress=lambda provider, pct, message, result: self._progress(
                        progress, "threat", pct, f"{provider.upper()}: {message}", case_id=case_id
                    ),
                )
                repository.add_case_evidence(
                    case_id, "THREAT_INTEL", "Autonomous threat intelligence package",
                    source="BLACKTERM Threat Intelligence Center",
                    content=json.dumps(threat_result.to_dict(), indent=2),
                )
                summaries.append(threat_result.summary)
                self._progress(progress, "threat", 100, "Threat intelligence complete.", case_id=case_id)
                self._event("Threat Intelligence Complete", threat_result.summary, module="threat",
                            target=target, case_id=case_id,
                            level_name="WARNING" if threat_result.threat_score >= 30 else "SUCCESS")

            if options.run_ai_correlation:
                self._progress(progress, "correlation", 20, "Evidence correlation initialized.", case_id=case_id)
                self._event("AI Correlation Started", "Cross-module evidence correlation is running.",
                            module="ai", target=target, case_id=case_id, level_name="AI")
                try:
                    correlation = correlate_case(repository, case_id)
                    correlation_text = correlation.to_text() if hasattr(correlation, "to_text") else str(correlation)
                except Exception as exc:
                    correlation_text = (
                        "BLACKTERM AUTONOMOUS CORRELATION\n\n"
                        + "\n\n".join(summaries)
                        + f"\n\nCorrelation engine note: {exc}"
                    )
                repository.add_case_evidence(
                    case_id, "AI", "Autonomous cross-module correlation",
                    source="BLACKTERM AI Correlation Engine", content=correlation_text,
                )
                repository.add_case_note(case_id, "Autonomous workflow summary:\n" + "\n\n".join(summaries))
                self._progress(progress, "correlation", 100, "AI correlation complete.", case_id=case_id)
                self._event("AI Correlation Complete", "Recon, OSINT, and threat evidence were correlated.",
                            module="ai", target=target, case_id=case_id, level_name="AI")

            if options.generate_report:
                self._progress(progress, "report", 10, "Case report generation initialized.", case_id=case_id)
                self._event("Report Started", "Generating autonomous investigation report.",
                            module="report", target=target, case_id=case_id)
                reports_dir = Path.home() / ".blackterm-recon" / "reports"
                safe_target = "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in target)
                destination = reports_dir / f"case-{case_id}-{safe_target}.html"
                report_path = str(write_case_report(repository, case_id, destination, "html"))
                repository.add_case_evidence(
                    case_id, "REPORT", "Autonomous HTML investigation report",
                    source="BLACKTERM Reporting Engine", file_path=report_path,
                    content=f"Generated report: {report_path}",
                )
                self._progress(progress, "report", 100, "Report generated.", case_id=case_id, report_path=report_path)
                self._event("Report Complete", f"Investigation report generated at {report_path}.",
                            module="report", target=target, case_id=case_id, level_name="SUCCESS")

            repository.update_case_status(case_id, "REVIEW")
            repository.add_case_timeline(case_id, "AUTOMATION", "Autonomous workflow complete", report_path)
            final_summary = " ".join(summaries) or "Autonomous investigation completed."
            self._event("Investigation Complete", f"Case #{case_id} is ready for analyst review.",
                        module="workflow", target=target, case_id=case_id, level_name="SUCCESS")
            return AutonomousWorkflowResult(case_id, scan_id, target, "complete", report_path, final_summary)
        except Exception as exc:
            repository.update_case_status(case_id, "REVIEW")
            repository.add_case_timeline(case_id, "ERROR", "Autonomous workflow interrupted", str(exc))
            repository.add_case_note(case_id, f"Autonomous workflow requires review: {exc}")
            self._event("Investigation Failed", str(exc), module="workflow", target=target,
                        case_id=case_id, level_name="ERROR")
            raise
