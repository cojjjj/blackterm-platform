from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from .attack_surface import build_attack_surface
from .investigation_engine import assess_result
from .summary import build_summary


@dataclass(slots=True)
class AssistantReply:
    title: str
    body: str
    intent: str
    confidence: int = 0
    evidence_count: int = 0
    evidence_refs: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)


@dataclass(slots=True)
class AnalystBrief:
    target: str
    risk_level: str
    risk_score: int
    confidence: int
    status: str
    summary: str
    facts: list[str] = field(default_factory=list)
    inferences: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    evidence_count: int = 0

    def to_text(self) -> str:
        facts = "\n".join(f"• {item}" for item in self.facts) or "• No confirmed observations are available."
        inferences = "\n".join(f"• {item}" for item in self.inferences) or "• No analyst inference was generated."
        recommendations = "\n".join(f"• {item}" for item in self.recommendations) or "• No additional action suggested."
        return (
            f"TARGET: {self.target}\n"
            f"RISK: {self.risk_level} ({self.risk_score}/100)\n"
            f"CONFIDENCE: {self.confidence}%\n"
            f"STATUS: {self.status}\n\n"
            f"INVESTIGATION SUMMARY\n{self.summary}\n\n"
            f"CONFIRMED FACTS\n{facts}\n\n"
            f"ANALYST INFERENCES\n{inferences}\n\n"
            f"RECOMMENDED NEXT STEPS\n{recommendations}\n\n"
            "BLACKTERM labels direct observations as facts and interpretation as inference. "
            "This analysis does not establish exploitability."
        )


def _unique(items: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(item for item in items if item))


def _services(result) -> list[str]:
    return sorted({str(item.service or "unknown") for item in result.open_ports})


def _ports(result) -> list[int]:
    return [int(item.port) for item in result.open_ports]


def _technology_names(result) -> list[str]:
    names = [str(item.name) for item in getattr(result, "fingerprints", ()) if getattr(item, "name", None)]
    if names:
        return sorted(set(names))
    surface = build_attack_surface(result)
    return surface.technologies


def build_analyst_brief(result) -> AnalystBrief:
    if result is None:
        return AnalystBrief(
            target="No saved scan",
            risk_level="UNKNOWN",
            risk_score=0,
            confidence=0,
            status="AWAITING DATA",
            summary="Run an authorized scan to generate a grounded analyst brief.",
        )

    assessment = assess_result(result)
    surface = build_attack_surface(result)
    ports = _ports(result)
    services = _services(result)
    technologies = _technology_names(result)

    facts: list[str] = [
        f"{len(ports)} open TCP port(s) were observed on {result.ip}.",
    ]
    if getattr(result, "hostname", None):
        facts.append(f"The resolved hostname is {result.hostname}.")
    if ports:
        facts.append("Observed ports: " + ", ".join(f"TCP/{port}" for port in ports) + ".")
    if services:
        facts.append("Observed services: " + ", ".join(services) + ".")
    if technologies:
        facts.append("Technology signals: " + ", ".join(technologies) + ".")
    if getattr(result, "profile", None):
        facts.append(f"The scan used the {result.profile} profile.")

    inferences: list[str] = []
    if any(item in services for item in {"microsoft-ds", "netbios-ssn"}):
        inferences.append("Windows file-sharing exposure is likely and may require segmentation review.")
    if any(item in services for item in {"http", "https", "http-proxy", "https-alt"}):
        inferences.append("A web-facing attack surface is present and warrants HTTP, TLS, and header review.")
    if any(item in services for item in {"mysql", "postgresql", "mongodb", "redis", "ms-sql-s", "oracle"}):
        inferences.append("A database-oriented service may be reachable from the current assessment scope.")
    if any(item in services for item in {"ssh", "telnet", "vnc", "rdp", "ms-wbt-server"}):
        inferences.append("A remote-administration path may be reachable from the current scan vantage point.")
    if len(ports) >= 8:
        inferences.append("The breadth of exposed services increases review complexity and potential attack surface.")
    if not inferences:
        inferences.append("The observed service set is limited, but intended exposure and patch state still require validation.")

    recommendations = list(assessment.recommendations)
    for finding in surface.findings:
        if finding.recommendation:
            recommendations.append(finding.recommendation)
    recommendations.extend([
        "Compare the result with an earlier scan to identify exposure changes.",
        "Attach validated observations and operator notes to the relevant case.",
        "Export an investigation report before making changes to the target.",
    ])

    evidence_count = len(ports) + len(services) + len(technologies) + len(surface.findings)
    confidence = min(98, max(assessment.confidence, 48 + evidence_count * 4))
    status = "REVIEW REQUIRED" if surface.risk_score >= 25 else "MONITORING"

    return AnalystBrief(
        target=result.target,
        risk_level=surface.risk_level,
        risk_score=surface.risk_score,
        confidence=confidence,
        status=status,
        summary=assessment.summary,
        facts=_unique(facts),
        inferences=_unique(inferences),
        recommendations=_unique(recommendations)[:7],
        evidence_count=evidence_count,
    )


def explain_finding(query: str, result) -> AssistantReply:
    q = query.lower()
    brief = build_analyst_brief(result)
    services = _services(result)
    ports = _ports(result)

    explanations = {
        "smb": (
            "SMB / TCP 445",
            "FACT: SMB is commonly used for Windows file and printer sharing. SMB-related exposure is observed only when TCP/445, TCP/139, microsoft-ds, or netbios-ssn appears in the saved scan.\n\n"
            "INFERENCE: Internet- or cross-segment SMB exposure can increase lateral-movement and credential risk.\n\n"
            "SAFE ACTIONS:\n• Confirm the exposure is intentional.\n• Review SMB signing, guest access, supported versions, and source restrictions.\n• Validate patch posture using approved administrative tooling.",
            any(port in {139, 445} for port in ports) or any(service in {"microsoft-ds", "netbios-ssn"} for service in services),
        ),
        "ssh": (
            "SSH / TCP 22",
            "FACT: SSH is a remote administration protocol.\n\n"
            "INFERENCE: Reachable SSH may be expected, but weak credentials, broad source access, or outdated cryptography can increase risk.\n\n"
            "SAFE ACTIONS:\n• Confirm key-based authentication policy.\n• Review root-login settings and source allowlists.\n• Validate supported cryptographic algorithms.",
            22 in ports or "ssh" in services,
        ),
        "rdp": (
            "RDP / TCP 3389",
            "FACT: RDP provides Windows remote desktop access.\n\n"
            "INFERENCE: Broadly reachable RDP can increase credential and remote-access exposure.\n\n"
            "SAFE ACTIONS:\n• Restrict access through VPN or source allowlists.\n• Require MFA where supported.\n• Confirm Network Level Authentication and patch status.",
            3389 in ports or any(service in {"rdp", "ms-wbt-server"} for service in services),
        ),
        "web": (
            "WEB SERVICE",
            "FACT: HTTP-oriented services expose an application interface.\n\n"
            "INFERENCE: Risk depends on authentication, application behavior, headers, TLS, and exposed administrative routes.\n\n"
            "SAFE ACTIONS:\n• Review HTTP security headers and TLS configuration.\n• Inventory authentication boundaries.\n• Capture authorized evidence for the case.",
            any(port in {80, 443, 8080, 8443} for port in ports) or any(service in {"http", "https", "http-proxy", "https-alt"} for service in services),
        ),
    }
    for token, (title, text, observed) in explanations.items():
        if token in q or (token == "web" and any(term in q for term in {"http", "https", "website"})):
            observation = "OBSERVED IN CURRENT SCAN" if observed else "NOT OBSERVED IN CURRENT SCAN"
            return AssistantReply(
                title,
                f"{observation}\n\n{text}",
                "smb" if token == "smb" else "explanation",
                brief.confidence if observed else 55,
                brief.evidence_count,
            )
    return AssistantReply(
        "FINDING EXPLANATION",
        "Select or name a supported observation such as SMB, SSH, RDP, HTTP, or HTTPS. "
        "BLACKTERM will distinguish direct evidence from contextual interpretation.",
        "explanation",
        brief.confidence,
        brief.evidence_count,
    )


def answer_question(question: str, result) -> AssistantReply:
    q = question.strip().lower()
    if result is None:
        return AssistantReply(
            "NO SAVED SCAN",
            "Run an authorized scan first. BLACKTERM answers only from saved observations.",
            "empty",
        )

    brief = build_analyst_brief(result)
    services = _services(result)
    ports = _ports(result)

    if any(term in q for term in {"executive brief", "executive summary", "generate brief", "full brief"}):
        return AssistantReply("EXECUTIVE INVESTIGATION BRIEF", brief.to_text(), "brief", brief.confidence, brief.evidence_count)

    if any(term in q for term in {"confidence", "how sure", "certainty"}):
        return AssistantReply(
            "ANALYST CONFIDENCE",
            f"Current confidence is {brief.confidence}%.\n\n"
            f"The score is based on {brief.evidence_count} saved evidence signal(s), including ports, services, technologies, and generated surface findings. "
            "Confidence reflects evidence coverage, not proof of vulnerability.",
            "confidence",
            brief.confidence,
            brief.evidence_count,
        )

    if any(term in q for term in {"fact", "confirmed", "evidence", "what do we know"}):
        return AssistantReply(
            "CONFIRMED OBSERVATIONS",
            "\n".join(f"• {item}" for item in brief.facts),
            "facts",
            brief.confidence,
            brief.evidence_count,
        )

    if any(term in q for term in {"infer", "inference", "what might", "what does this suggest"}):
        return AssistantReply(
            "ANALYST INFERENCES",
            "\n".join(f"• {item}" for item in brief.inferences)
            + "\n\nThese are contextual interpretations and are not confirmed vulnerabilities.",
            "inferences",
            brief.confidence,
            brief.evidence_count,
        )

    if any(term in q for term in {"explain smb", "explain ssh", "explain rdp", "explain http", "explain https", "explain web"}):
        return explain_finding(q, result)

    if any(term in q for term in {"what ports", "open ports", "ports are open"}):
        body = "\n".join(f"• {item.port}/tcp — {item.service}" for item in result.open_ports) or "No open ports were observed in the selected range."
        return AssistantReply("OPEN TCP PORTS", body, "ports", brief.confidence, len(ports))

    if any(term in q for term in {"what services", "services found", "service list"}):
        body = "\n".join(f"• {service}" for service in services) or "No services observed."
        return AssistantReply("OBSERVED SERVICES", body, "services", brief.confidence, len(services))

    if "smb" in q:
        return explain_finding("smb", result)

    if any(term in q for term in {"should i worry", "is this bad", "dangerous", "risk", "why risky"}):
        body = (
            f"RISK: {brief.risk_level} ({brief.risk_score}/100)\n"
            f"CONFIDENCE: {brief.confidence}%\n\n"
            f"{brief.summary}\n\n"
            "WHY:\n" + "\n".join(f"• {item}" for item in brief.inferences) +
            "\n\nNo vulnerability is established from service exposure alone."
        )
        return AssistantReply("CONTEXTUAL RISK ASSESSMENT", body, "assessment", brief.confidence, brief.evidence_count)

    if any(term in q for term in {"what stands out", "stand out", "interesting"}):
        body = "\n".join(build_summary(result)) + "\n\nHIGH-SIGNAL CONTEXT\n" + "\n".join(f"• {item}" for item in brief.inferences[:3])
        return AssistantReply("WHAT STANDS OUT", body, "summary", brief.confidence, brief.evidence_count)

    if any(term in q for term in {"recommend", "next step", "what next", "next action"}):
        return AssistantReply(
            "SAFE NEXT STEPS",
            "\n".join(f"• {action}" for action in brief.recommendations),
            "recommendations",
            brief.confidence,
            brief.evidence_count,
        )

    if any(term in q for term in {"summarize", "summary", "latest scan", "investigation summary"}):
        body = (
            f"{brief.summary}\n\n"
            f"RISK: {brief.risk_level} ({brief.risk_score}/100)\n"
            f"CONFIDENCE: {brief.confidence}%\n"
            f"EVIDENCE SIGNALS: {brief.evidence_count}"
        )
        return AssistantReply("INVESTIGATION SUMMARY", body, "summary", brief.confidence, brief.evidence_count)

    if any(term in q for term in {"latency", "response time", "fast"}):
        return AssistantReply(
            "LATENCY",
            f"Average latency across observed open ports: {result.average_open_latency} ms.",
            "latency",
            brief.confidence,
            len(ports),
        )

    return AssistantReply(
        "GROUNDED ANALYST RESPONSE",
        brief.to_text() + "\n\nTry asking: why is this risky, what do we know, what might this suggest, explain SMB, or generate executive brief.",
        "fallback",
        brief.confidence,
        brief.evidence_count,
    )


@dataclass(slots=True)
class CaseAnalystBrief:
    case_id: int
    target: str
    risk_level: str
    risk_score: int
    confidence: int
    evidence_count: int
    status: str
    assessment: str
    facts: list[str] = field(default_factory=list)
    inferences: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    memory: list[str] = field(default_factory=list)
    findings: list[str] = field(default_factory=list)

    def to_text(self) -> str:
        def section(title: str, values: list[str], fallback: str) -> str:
            body = "\n".join(f"• {item}" for item in values) or f"• {fallback}"
            return f"{title}\n{body}"
        return (
            f"BLACKTERM AI ANALYST // CASE #{self.case_id}\n\n"
            f"TARGET: {self.target}\nRISK: {self.risk_level} ({self.risk_score}/100)\n"
            f"CONFIDENCE: {self.confidence}%\nSTATUS: {self.status}\n\n"
            f"ASSESSMENT\n{self.assessment}\n\n"
            f"{section('CONFIRMED FACTS', self.facts, 'No confirmed observations are available.')}\n\n"
            f"{section('ANALYST ASSESSMENT', self.inferences, 'No additional inference was generated.')}\n\n"
            f"{section('INVESTIGATION MEMORY', self.memory, 'No comparable earlier scan was found.')}\n\n"
            f"{section('RECOMMENDED ACTIONS', self.recommendations, 'No additional action suggested.')}\n\n"
            "Analyst note: exposure is not proof of exploitability. Validate every conclusion with authorized evidence."
        )


def _scan_port_set(result) -> set[int]:
    return {int(item.port) for item in getattr(result, "open_ports", ()) if getattr(item, "state", "open") == "open"}


def _historical_comparison(repository, current_result, current_scan_id: int | None = None) -> list[str]:
    if current_result is None:
        return []
    candidates = []
    for row in repository.list_recent(300):
        if row.get("target") != current_result.target or row.get("id") == current_scan_id:
            continue
        previous = repository.get(row["id"])
        if previous:
            candidates.append((row["id"], previous))
    if not candidates:
        return ["No earlier saved scan of this target is available for comparison."]
    previous_id, previous = candidates[0]
    current_ports = _scan_port_set(current_result)
    previous_ports = _scan_port_set(previous)
    added = sorted(current_ports - previous_ports)
    removed = sorted(previous_ports - current_ports)
    messages = [f"Compared with saved scan #{previous_id} of the same target."]
    if added:
        messages.append("Newly observed exposure: " + ", ".join(f"TCP/{p}" for p in added) + ".")
    if removed:
        messages.append("No longer observed: " + ", ".join(f"TCP/{p}" for p in removed) + ".")
    if not added and not removed:
        messages.append("The observed open-port set is unchanged from the earlier scan.")
    return messages


def build_case_analyst_brief(repository, case_id: int) -> CaseAnalystBrief:
    from .investigation_engine import assess_case

    scans = repository.case_scans(case_id)
    results = [repository.get(scan["id"]) for scan in scans]
    results = [result for result in results if result]
    evidence = repository.case_evidence(case_id)
    notes = repository.case_notes(case_id)
    assessment = assess_case(repository, case_id)
    latest = results[0] if results else None
    target = latest.target if latest else f"Case #{case_id}"
    ports = sorted({p for result in results for p in _scan_port_set(result)})
    services = sorted({str(item.service or "unknown") for result in results for item in result.open_ports})

    facts = [
        f"{len(scans)} scan(s) are attached to this case.",
        f"{len(ports)} unique open TCP port(s) were observed.",
        f"{len(evidence)} evidence item(s) and {len(notes)} operator note(s) are stored.",
    ]
    if ports:
        facts.append("Observed ports: " + ", ".join(f"TCP/{p}" for p in ports) + ".")
    if services:
        facts.append("Observed services: " + ", ".join(services) + ".")

    inferences = []
    if 445 in ports or "microsoft-ds" in services:
        inferences.append("SMB exposure is reachable from the scan vantage point and deserves segmentation, signing, guest-access, and version review.")
    if 3389 in ports or "ms-wbt-server" in services:
        inferences.append("A remote desktop administration path may be reachable and should be restricted to approved sources.")
    if any(port in ports for port in (80, 443, 8080, 8443)):
        inferences.append("A web-facing surface is present; application behavior, authentication, headers, and TLS require separate validation.")
    if not inferences:
        inferences.append("The current exposure appears limited, but intended access and patch posture still require validation.")

    recommendations = list(assessment.recommendations)
    if 445 in ports:
        recommendations.extend([
            "Review SMB versions, message signing, guest access, and source restrictions.",
            "Confirm whether TCP/445 exposure is intentional for this network segment.",
        ])
    recommendations.extend([
        "Compare changes against the investigation timeline before remediation.",
        "Attach validation evidence and operator notes before closing the case.",
    ])
    confidence = min(98, max(assessment.confidence, 50 + min(35, len(evidence) * 3 + len(ports) * 4 + len(notes) * 2)))
    status = "ACTION RECOMMENDED" if assessment.score >= 40 else "MONITORING"
    memory = _historical_comparison(repository, latest, scans[0]["id"] if scans else None)
    findings = list(assessment.findings) or ["No high-confidence finding was generated."]
    return CaseAnalystBrief(
        case_id=case_id,
        target=target,
        risk_level=assessment.level,
        risk_score=assessment.score,
        confidence=confidence,
        evidence_count=len(evidence) + len(ports) + len(services),
        status=status,
        assessment=assessment.summary,
        facts=_unique(facts),
        inferences=_unique(inferences),
        recommendations=_unique(recommendations)[:7],
        memory=_unique(memory),
        findings=_unique(findings),
    )



def _case_evidence_references(repository, case_id: int, brief: CaseAnalystBrief) -> list[str]:
    """Return short, human-readable references to the saved evidence supporting a reply."""
    refs: list[str] = []
    scans = repository.case_scans(case_id)
    if scans:
        latest = scans[0]
        refs.append(f"Saved scan #{latest['id']}")
    evidence = repository.case_evidence(case_id)
    for item in evidence[:3]:
        title = str(item.get("title") or item.get("evidence_type") or "Evidence item")
        refs.append(title)
    if brief.facts:
        refs.append("Confirmed case observations")
    return _unique(refs)[:5]


def _case_suggestions(brief: CaseAnalystBrief) -> list[str]:
    suggestions = [
        "Summarize this case",
        "Why is this risky?",
        "What changed since the previous scan?",
        "What should I do next?",
        "Explain every open port",
        "Generate an executive brief",
    ]
    joined = " ".join(brief.facts + brief.inferences + brief.findings).lower()
    if "smb" in joined or "445" in joined:
        suggestions.insert(4, "Explain SMB")
    if "rdp" in joined or "3389" in joined:
        suggestions.insert(4, "Explain RDP")
    return _unique(suggestions)[:8]


def investigation_quality(repository, case_id: int) -> tuple[int, list[str]]:
    """Estimate investigation completeness from saved case artifacts, not target risk."""
    scans = repository.case_scans(case_id)
    evidence = repository.case_evidence(case_id)
    notes = repository.case_notes(case_id)
    timeline = repository.case_timeline(case_id)
    score = 0
    reasons: list[str] = []
    if scans:
        score += 30
        reasons.append("A saved scan is attached")
    if evidence:
        score += min(30, 10 + len(evidence) * 5)
        reasons.append(f"{len(evidence)} evidence item(s) are stored")
    if notes:
        score += min(15, 5 + len(notes) * 3)
        reasons.append(f"{len(notes)} operator note(s) add context")
    if timeline:
        score += min(15, 5 + len(timeline) * 2)
        reasons.append("The investigation timeline is populated")
    if len(scans) > 1:
        score += 10
        reasons.append("Historical scan comparison is available")
    return min(100, score), reasons


def _port_explanations(repository, case_id: int) -> list[str]:
    scans = repository.case_scans(case_id)
    if not scans:
        return ["No attached scan is available."]
    latest = repository.get(scans[0]["id"])
    if latest is None:
        return ["The attached scan could not be loaded."]
    descriptions = {
        22: "SSH remote administration; validate authentication policy and source restrictions.",
        25: "SMTP mail transfer; review relay behavior, TLS, and authentication controls.",
        53: "DNS service; review recursion, zone-transfer controls, and intended exposure.",
        80: "HTTP web service; review application routes, authentication, and security headers.",
        135: "Microsoft RPC endpoint mapper; commonly internal and should be reviewed for segmentation.",
        139: "NetBIOS session service; associated with legacy Windows file sharing.",
        443: "HTTPS web service; review certificate, TLS configuration, and application behavior.",
        445: "SMB / Microsoft-DS; review signing, guest access, versions, and network exposure.",
        3389: "RDP remote desktop; restrict to approved sources and require strong authentication.",
        8080: "Alternate HTTP service; may expose an application or administrative interface.",
        8443: "Alternate HTTPS service; may expose a management or application interface.",
    }
    lines = []
    for item in latest.open_ports:
        port = int(item.port)
        service = str(item.service or "unknown")
        context = descriptions.get(port, "Validate whether this service is intended, patched, and appropriately restricted.")
        lines.append(f"TCP/{port} — {service}: {context}")
    return lines or ["No open TCP ports were observed in the selected scan range."]


def answer_case_question(question: str, repository, case_id: int) -> AssistantReply:
    brief = build_case_analyst_brief(repository, case_id)
    q = question.strip().lower()
    refs = _case_evidence_references(repository, case_id, brief)
    suggestions = _case_suggestions(brief)

    def reply(title: str, body: str, intent: str, evidence_count: int | None = None) -> AssistantReply:
        return AssistantReply(
            title,
            body,
            intent,
            brief.confidence,
            brief.evidence_count if evidence_count is None else evidence_count,
            refs,
            suggestions,
        )

    if any(term in q for term in ("quality", "coverage", "complete", "completeness")):
        score, reasons = investigation_quality(repository, case_id)
        body = f"INVESTIGATION QUALITY: {score}%\n\n" + "\n".join(f"• {item}" for item in reasons)
        body += "\n\nThis measures case coverage and documentation, not target security."
        return reply("INVESTIGATION QUALITY", body, "quality")

    if any(term in q for term in ("memory", "changed", "previous", "before", "difference", "compare")):
        return reply("INVESTIGATION MEMORY", "\n".join(f"• {x}" for x in brief.memory), "memory")

    if any(term in q for term in ("every port", "every open port", "all ports", "explain ports")):
        return reply("OPEN PORT EXPLANATIONS", "\n\n".join(f"• {x}" for x in _port_explanations(repository, case_id)), "ports")

    if any(term in q for term in ("why", "risk", "worry", "danger")):
        body = (
            f"{brief.assessment}\n\n"
            + "\n".join(f"• {x}" for x in brief.inferences)
            + "\n\nNo exploitability was confirmed. The assessment is based on saved exposure evidence."
        )
        return reply("RISK EXPLANATION", body, "risk")

    if any(term in q for term in ("next", "recommend", "do now", "action")):
        return reply("RECOMMENDED ACTIONS", "\n".join(f"• {x}" for x in brief.recommendations), "next")

    if any(term in q for term in ("brief", "summary", "report")):
        return reply("EXECUTIVE BRIEF", brief.to_text(), "brief")

    if "smb" in q or "445" in q:
        latest = repository.get(repository.case_scans(case_id)[0]["id"]) if repository.case_scans(case_id) else None
        base = explain_finding("smb", latest)
        base.evidence_refs = refs
        base.suggestions = suggestions
        return base

    if "rdp" in q or "3389" in q:
        latest = repository.get(repository.case_scans(case_id)[0]["id"]) if repository.case_scans(case_id) else None
        base = explain_finding("rdp", latest)
        base.evidence_refs = refs
        base.suggestions = suggestions
        return base

    if any(term in q for term in ("fact", "evidence", "know", "confirmed")):
        return reply("CONFIRMED CASE EVIDENCE", "\n".join(f"• {x}" for x in brief.facts), "facts")

    return reply(
        "AI ANALYST",
        brief.assessment
        + "\n\nAsk about risk, next actions, open ports, investigation quality, historical changes, or request an executive brief.",
        "overview",
    )

