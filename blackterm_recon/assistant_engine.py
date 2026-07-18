from __future__ import annotations

from dataclasses import dataclass

from .summary import build_summary


@dataclass(slots=True)
class AssistantReply:
    title: str
    body: str
    intent: str


def _services(result) -> list[str]:
    return sorted({item.service for item in result.open_ports})


def _ports(result) -> list[int]:
    return [item.port for item in result.open_ports]


def answer_question(question: str, result) -> AssistantReply:
    q = question.strip().lower()
    if result is None:
        return AssistantReply(
            "NO SAVED SCAN",
            "Run an authorized scan first. BLACKTERM answers only from saved observations.",
            "empty",
        )

    services = _services(result)
    ports = _ports(result)

    if any(term in q for term in {"what ports", "open ports", "ports are open"}):
        body = "\n".join(
            f"• {item.port}/tcp — {item.service}"
            for item in result.open_ports
        ) or "No open ports were observed in the selected range."
        return AssistantReply("OPEN TCP PORTS", body, "ports")

    if any(term in q for term in {"what services", "services found", "service list"}):
        body = "\n".join(f"• {service}" for service in services) or "No services observed."
        return AssistantReply("OBSERVED SERVICES", body, "services")

    if "smb" in q:
        present = any(service in {"microsoft-ds", "netbios-ssn"} for service in services)
        body = (
            "SMB is commonly used for Windows file and printer sharing.\n\n"
            + (
                "Observed evidence: TCP 445 or related Windows file-sharing service is reachable."
                if present
                else "No SMB-related service was observed in the latest saved scan."
            )
            + "\n\nThis confirms service exposure only; it does not establish a vulnerability."
        )
        return AssistantReply("SMB EXPLANATION", body, "smb")

    if any(term in q for term in {"should i worry", "is this bad", "dangerous", "risk"}):
        body = (
            f"The latest scan observed {len(ports)} open TCP port(s). "
            "Whether that is expected depends on the intended role of the host.\n\n"
            "No vulnerability was detected from this scan alone. Review unexpected services, "
            "compare with earlier scans, and confirm exposure is intentional."
        )
        return AssistantReply("CONTEXTUAL ASSESSMENT", body, "assessment")

    if any(term in q for term in {"what stands out", "stand out", "interesting"}):
        return AssistantReply(
            "WHAT STANDS OUT",
            "\n".join(build_summary(result)),
            "summary",
        )

    if any(term in q for term in {"recommend", "next step", "what next"}):
        actions = []
        if any(service in {"microsoft-ds", "netbios-ssn"} for service in services):
            actions.append("Confirm Windows file-sharing exposure is intentional.")
        if any(service in {"http", "https", "http-proxy"} for service in services):
            actions.append("Review HTTP headers and TLS configuration.")
        if "ssh" in services:
            actions.append("Confirm SSH is restricted to the intended network scope.")
        if any(service in {"mysql", "postgresql", "redis", "mongodb"} for service in services):
            actions.append("Confirm database services are limited to trusted hosts.")
        actions.extend([
            "Compare this result with an earlier scan.",
            "Attach the scan to a case if it belongs to an investigation.",
            "Export a report before changing the host.",
        ])
        return AssistantReply(
            "SAFE NEXT STEPS",
            "\n".join(f"• {action}" for action in actions),
            "recommendations",
        )

    if any(term in q for term in {"summarize", "summary", "latest scan"}):
        return AssistantReply(
            "LATEST SCAN SUMMARY",
            "\n".join(build_summary(result)),
            "summary",
        )

    if any(term in q for term in {"latency", "response time", "fast"}):
        return AssistantReply(
            "LATENCY",
            f"Average latency across observed open ports: {result.average_open_latency} ms.",
            "latency",
        )

    return AssistantReply(
        "GROUNDED RESPONSE",
        "\n".join(build_summary(result))
        + "\n\nTry asking about ports, services, SMB, risk context, or next steps.",
        "fallback",
    )
