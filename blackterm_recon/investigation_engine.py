from __future__ import annotations

from dataclasses import dataclass


SENSITIVE_PORTS = {
    21: ("FTP", 12, "Prefer SFTP/FTPS and verify anonymous access is disabled."),
    23: ("Telnet", 25, "Disable Telnet and replace it with an encrypted management protocol."),
    139: ("NetBIOS", 12, "Review legacy Windows file-sharing exposure and segmentation."),
    445: ("SMB", 20, "Review SMB versions, signing, guest access, and network exposure."),
    3389: ("RDP", 20, "Restrict RDP with MFA, a VPN, and network-level access controls."),
    5900: ("VNC", 18, "Restrict VNC exposure and require strong encrypted authentication."),
}


@dataclass(frozen=True, slots=True)
class InvestigationAssessment:
    score: int
    level: str
    summary: str
    recommendations: tuple[str, ...]
    confidence: int = 60
    findings: tuple[str, ...] = ()

    def to_text(self) -> str:
        findings = "\n".join(f"- {item}" for item in self.findings) or "- No high-signal finding was automatically confirmed."
        recommendations = "\n".join(f"{index}. {item}" for index, item in enumerate(self.recommendations, 1))
        return (
            "BLACKTERM AI INVESTIGATION\n\n"
            f"RISK LEVEL: {self.level}\n"
            f"CONTEXT SCORE: {self.score}/100\n"
            f"CONFIDENCE: {self.confidence}%\n\n"
            f"SUMMARY\n{self.summary}\n\n"
            f"FINDINGS\n{findings}\n\n"
            f"RECOMMENDED NEXT STEPS\n{recommendations}\n\n"
            "AI output is advisory and does not establish vulnerability."
        )


def _level(score: int) -> str:
    if score >= 75:
        return "CRITICAL"
    if score >= 50:
        return "ELEVATED"
    if score >= 25:
        return "GUARDED"
    return "LOW"


def assess_result(result) -> InvestigationAssessment:
    open_items = list(getattr(result, "open_ports", []) or [])
    ports = [int(item.port) for item in open_items]
    services = sorted({str(item.service or "unknown") for item in open_items})
    score = min(35, len(open_items) * 4)
    recommendations: list[str] = []
    findings: list[str] = []

    for port in ports:
        item = SENSITIVE_PORTS.get(port)
        if item:
            name, weight, recommendation = item
            score += weight
            findings.append(f"{name} exposure observed on TCP/{port}.")
            recommendations.append(recommendation)

    if 80 in ports or 8080 in ports:
        score += 6
        findings.append("A web service is reachable and should be reviewed for authentication and exposed administration paths.")
        recommendations.append("Review web headers, authentication boundaries, and exposed administrative paths.")
    if 22 in ports:
        findings.append("SSH is reachable from the selected scan vantage point.")
        recommendations.append("Confirm SSH key policy, root-login settings, and supported cryptographic algorithms.")
    if not open_items:
        recommendations.append("Validate host reachability and scan coverage before closing the investigation.")
    elif not recommendations:
        recommendations.append("Validate that each exposed service is expected, patched, authenticated, and appropriately segmented.")

    score = max(5, min(100, score))
    confidence = min(96, 52 + len(open_items) * 6 + len(findings) * 5)
    target = getattr(result, "target", "unknown target")
    if findings:
        summary = f"{target} exposed {len(open_items)} open TCP service(s). " + " ".join(findings[:2])
    elif services:
        summary = f"{target} exposed {len(open_items)} open TCP service(s): {', '.join(services)}."
    else:
        summary = f"No open TCP services were observed for {target} in the selected scope."

    return InvestigationAssessment(
        score=score,
        level=_level(score),
        summary=summary,
        recommendations=tuple(dict.fromkeys(recommendations)),
        confidence=confidence,
        findings=tuple(dict.fromkeys(findings)),
    )


def assess_case(repository, case_id: int) -> InvestigationAssessment:
    scans = repository.case_scans(case_id)
    evidence = repository.case_evidence(case_id)
    notes = repository.case_notes(case_id)
    results = [repository.get(scan["id"]) for scan in scans]
    results = [result for result in results if result]

    all_ports = [port for result in results for port in result.open_ports]
    proxy = type("CaseResult", (), {
        "target": f"Case #{case_id}",
        "open_ports": all_ports,
    })()
    base = assess_result(proxy)
    score = min(100, base.score + min(15, len(evidence) * 2) + min(8, len(notes)))
    confidence = min(98, base.confidence + min(15, len(evidence) * 2) + min(8, len(notes)))
    findings = list(base.findings)
    if len(scans) > 1:
        findings.append(f"The case correlates {len(scans)} scans across the investigation timeline.")
    if evidence:
        findings.append(f"{len(evidence)} evidence item(s) are available for analyst validation.")
    summary = (
        f"Case #{case_id} contains {len(scans)} scan(s), {len(all_ports)} open-port observation(s), "
        f"{len(evidence)} evidence item(s), and {len(notes)} analyst note(s). {base.summary}"
    )
    return InvestigationAssessment(
        score=score,
        level=_level(score),
        summary=summary,
        recommendations=base.recommendations,
        confidence=confidence,
        findings=tuple(dict.fromkeys(findings)),
    )
