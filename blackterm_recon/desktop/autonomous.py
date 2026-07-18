from __future__ import annotations

from datetime import datetime, timezone
import json
from typing import Iterable

from PySide6.QtCore import QObject, Qt, QTimer, Signal, Slot

from ..events import EventLevel
from ..investigation_engine import InvestigationAssessment, SENSITIVE_PORTS, assess_result


class AutonomousInvestigation(QObject):
    """Thread-safe bridge from scan telemetry into cases and evidence."""

    case_created = Signal(int)
    investigation_completed = Signal(int, object)
    _scan_started = Signal(str)
    _port_observed = Signal(str, object)
    _scan_completed = Signal(int, object)

    def __init__(self, engine, event_bus, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.event_bus = event_bus
        self._target = ""
        self._open_findings: list[dict] = []
        self._scan_started.connect(self._handle_scan_started, Qt.QueuedConnection)
        self._port_observed.connect(self._handle_port_observed, Qt.QueuedConnection)
        self._scan_completed.connect(self._handle_scan_completed, Qt.QueuedConnection)

    def scan_started(self, target: str) -> None:
        self._scan_started.emit(target)

    def port_observed(self, target: str, item) -> None:
        self._port_observed.emit(target, item)

    def scan_completed(self, scan_id: int, result) -> None:
        self._scan_completed.emit(scan_id, result)

    def _emit(self, category: str, message: str, *, title: str,
              level=EventLevel.INFO, scan_id: int | None = None,
              metadata: dict | None = None) -> None:
        if self.event_bus:
            self.event_bus.emit(category, message, title=title, level=level,
                                scan_id=scan_id, module="investigation",
                                metadata=metadata or {})

    @Slot(str)
    def _handle_scan_started(self, target: str) -> None:
        self._target = target
        self._open_findings = []
        phases = [
            (80, "Target Identified", f"Target {target} entered the autonomous investigation pipeline."),
            (420, "Scope Registered", "Authorized scope registered and evidence collection initialized."),
            (820, "AI Analyst Activated", "The analyst is correlating live port, service, and timing telemetry."),
        ]
        for delay, title, message in phases:
            QTimer.singleShot(delay, lambda t=title, m=message: self._emit(
                "investigation", m, title=t,
                level=EventLevel.AI if "AI" in t else EventLevel.INFO,
                metadata={"target": target},
            ))

    @Slot(str, object)
    def _handle_port_observed(self, target: str, item) -> None:
        finding = {
            "port": int(item.port),
            "service": str(item.service or "unknown"),
            "latency_ms": float(item.latency_ms or 0),
            "banner": str(item.banner or ""),
        }
        self._open_findings.append(finding)
        sensitive = finding["port"] in SENSITIVE_PORTS
        self._emit("investigation",
                   f"Evidence candidate recorded for TCP/{finding['port']} ({finding['service']}).",
                   title="Evidence Candidate",
                   level=EventLevel.WARNING if sensitive else EventLevel.SUCCESS,
                   metadata={"target": target, **finding})

    @Slot(int, object)
    def _handle_scan_completed(self, scan_id: int, result) -> None:
        assessment = assess_result(result)
        repository = self.engine.repository
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        target = getattr(result, "target", self._target or "unknown")
        case_id = repository.create_case(
            f"AUTO-{timestamp} // {target}",
            "Automatically created after an authorized reconnaissance scan.",
        )
        repository.update_case_status(case_id, "ACTIVE")
        repository.attach_scan_to_case(case_id, scan_id)
        repository.add_case_timeline(case_id, "AUTOMATION", "Autonomous investigation started", target)

        evidence_payload = {
            "scan_id": scan_id,
            "target": target,
            "ip": getattr(result, "ip", ""),
            "hostname": getattr(result, "hostname", ""),
            "duration_seconds": getattr(result, "duration_seconds", 0),
            "open_ports": self._open_findings,
            "risk_score": assessment.score,
            "risk_level": assessment.level,
            "confidence": assessment.confidence,
        }
        repository.add_case_evidence(case_id, "SCAN", f"Reconnaissance result #{scan_id}",
                                     source="BLACKTERM Recon Engine",
                                     content=json.dumps(evidence_payload, indent=2))
        repository.add_case_evidence(case_id, "AI", "Autonomous investigation assessment",
                                     source="BLACKTERM AI Analyst",
                                     content=assessment.to_text())
        repository.add_case_note(case_id,
                                 f"Autonomous triage completed: {assessment.level} risk, "
                                 f"score {assessment.score}/100, confidence {assessment.confidence}%.")
        self.case_created.emit(case_id)
        self._stream_completion(case_id, scan_id, assessment)

    def _stream_completion(self, case_id: int, scan_id: int,
                           assessment: InvestigationAssessment) -> None:
        steps: Iterable[tuple[int, str, str, EventLevel]] = (
            (100, "Telemetry Correlated", assessment.summary, EventLevel.AI),
            (520, "Evidence Secured", f"Scan #{scan_id} and AI findings were hashed and stored in Case #{case_id}.", EventLevel.SUCCESS),
            (940, "Threat Context Updated", f"Context score: {assessment.score}/100 ({assessment.level}), confidence {assessment.confidence}%.", EventLevel.WARNING if assessment.score >= 50 else EventLevel.INFO),
            (1360, "Case Created", f"Case #{case_id} is active and ready for analyst review.", EventLevel.SUCCESS),
            (1780, "AI Investigation Finished", assessment.recommendations[0], EventLevel.AI),
        )
        for delay, title, message, level in steps:
            QTimer.singleShot(delay, lambda t=title, m=message, l=level: self._emit(
                "case", m, title=t, level=l, scan_id=scan_id,
                metadata={"case_id": case_id, "score": assessment.score,
                          "risk": assessment.level, "confidence": assessment.confidence},
            ))
        QTimer.singleShot(1850, lambda: self.investigation_completed.emit(case_id, assessment))
