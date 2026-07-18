from __future__ import annotations

DEVICE_COLORS = {
    "windows": "#31b7ff",
    "linux": "#35df83",
    "web": "#ffb000",
    "network": "#ff7a00",
    "database": "#9a7dff",
    "remote": "#00d7c7",
    "unknown": "#ff5c7a",
    "core": "#c000ff",
}

DEVICE_GLYPHS = {
    "windows": "▣",
    "linux": "◇",
    "web": "◈",
    "network": "◎",
    "database": "▤",
    "remote": "⌁",
    "unknown": "?",
    "core": "◆",
}

SERVICE_GROUPS = {
    "windows": {"microsoft-ds", "epmap", "netbios-ssn", "ms-wbt-server"},
    "linux": {"ssh"},
    "web": {"http", "https", "http-proxy"},
    "network": {"domain", "snmp", "bootps", "ntp"},
    "database": {"mysql", "postgresql", "redis", "mongodb", "ms-sql-s"},
    "remote": {"vnc", "telnet"},
}


def classify_host(services: set[str]) -> tuple[str, str]:
    lowered = {service.lower() for service in services}
    for group in ("windows", "database", "network", "linux", "web", "remote"):
        if lowered & SERVICE_GROUPS[group]:
            labels = {
                "windows": "Windows host",
                "database": "Database service host",
                "network": "Network infrastructure",
                "linux": "Unix/Linux-like host",
                "web": "Web service host",
                "remote": "Remote-access host",
            }
            return group, labels[group]
    return "unknown", "Unknown host type"


def exposure_score(open_ports: list[int], services: list[str]) -> tuple[int, str]:
    """A visibility score, not a vulnerability score."""
    score = min(100, len(open_ports) * 9)
    lowered = {service.lower() for service in services}
    if lowered & {"telnet", "vnc"}:
        score += 18
    if lowered & {"microsoft-ds", "ms-wbt-server"}:
        score += 8
    if lowered & {"http", "https", "http-proxy"}:
        score += 5
    score = min(100, score)
    if score < 20:
        label = "LOW EXPOSURE"
    elif score < 45:
        label = "MODERATE EXPOSURE"
    elif score < 70:
        label = "ELEVATED EXPOSURE"
    else:
        label = "HIGH EXPOSURE"
    return score, label


def exposure_color(score: int) -> str:
    if score < 20:
        return "#35df83"
    if score < 45:
        return "#ffd166"
    if score < 70:
        return "#ff9f43"
    return "#ff5c7a"


def explain_host(profile) -> str:
    services = set(profile.services)
    score, label = exposure_score(profile.open_ports, profile.services)
    observations = [
        f"Observed {profile.open_count} open TCP port(s).",
        f"Service pattern: {profile.device_label}.",
        f"Exposure index: {score}/100 — {label}.",
    ]

    recommendations = []
    if services & {"microsoft-ds", "netbios-ssn"}:
        recommendations.append("Confirm Windows file-sharing exposure is intentional.")
    if services & {"http", "https", "http-proxy"}:
        recommendations.append("Review HTTP headers and TLS configuration.")
    if "ssh" in services:
        recommendations.append("Confirm SSH is limited to the intended network scope.")
    if services & {"mysql", "postgresql", "redis", "mongodb", "ms-sql-s"}:
        recommendations.append("Confirm database services are not exposed beyond trusted hosts.")
    if services & {"telnet", "vnc"}:
        recommendations.append("Review remote-access controls and prefer encrypted administration.")
    recommendations.append("Compare with an earlier scan to identify unexpected changes.")
    recommendations.append("Export a report before modifying the host.")

    return "\n".join(
        ["OBSERVATIONS", *[f"• {item}" for item in observations], "", "SAFE NEXT STEPS",
         *[f"• {item}" for item in recommendations]]
    )
