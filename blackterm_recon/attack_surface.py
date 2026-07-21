from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Iterable

from .models import PortResult, ScanResult


SEVERITY_WEIGHTS = {
    "critical": 35,
    "high": 22,
    "medium": 12,
    "low": 5,
    "info": 0,
}

RISKY_SERVICES = {
    "telnet": ("high", "Clear-text remote administration service is exposed."),
    "ftp": ("medium", "FTP is exposed; verify encryption and anonymous access settings."),
    "microsoft-ds": ("medium", "SMB is reachable and should be limited to trusted networks."),
    "netbios-ssn": ("medium", "NetBIOS file-sharing exposure was observed."),
    "vnc": ("high", "Remote desktop service is exposed; require strong authentication and network controls."),
    "rdp": ("medium", "Remote Desktop is reachable; restrict source networks and enforce MFA where possible."),
    "ms-wbt-server": ("medium", "Remote Desktop is reachable; restrict source networks and enforce MFA where possible."),
    "redis": ("high", "Redis exposure can be dangerous when authentication or network restrictions are weak."),
    "mongodb": ("high", "MongoDB exposure should be reviewed for authentication and network restrictions."),
}

WEB_SERVICES = {"http", "https", "http-proxy", "https-alt"}
REMOTE_ADMIN_SERVICES = {"ssh", "telnet", "vnc", "rdp", "ms-wbt-server"}
DATABASE_SERVICES = {"mysql", "postgresql", "mongodb", "redis", "ms-sql-s", "oracle"}


@dataclass(slots=True)
class SurfaceFinding:
    severity: str
    title: str
    detail: str
    evidence: str = ""
    recommendation: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class AttackSurface:
    target: str
    ip: str
    hostname: str | None
    operation_id: str | None
    profile: str
    open_ports: list[int] = field(default_factory=list)
    services: list[str] = field(default_factory=list)
    technologies: list[str] = field(default_factory=list)
    findings: list[SurfaceFinding] = field(default_factory=list)
    exposure_categories: dict[str, int] = field(default_factory=dict)
    risk_score: int = 0
    risk_level: str = "LOW"
    attack_surface_score: int = 100

    @property
    def severity_counts(self) -> dict[str, int]:
        counts = {key: 0 for key in ("critical", "high", "medium", "low", "info")}
        for finding in self.findings:
            counts[finding.severity] = counts.get(finding.severity, 0) + 1
        return counts

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["severity_counts"] = self.severity_counts
        return data


def _unique(values: Iterable[str]) -> list[str]:
    return sorted({value for value in values if value})


def _detect_technologies(ports: list[PortResult], plugin_results: dict[str, Any]) -> list[str]:
    detected: list[str] = []
    signatures = {
        "apache": "Apache",
        "nginx": "Nginx",
        "microsoft-iis": "Microsoft IIS",
        "iis": "Microsoft IIS",
        "openssh": "OpenSSH",
        "cloudflare": "Cloudflare",
        "wordpress": "WordPress",
        "express": "Express",
        "node.js": "Node.js",
        "php": "PHP",
    }
    for port in ports:
        haystack = f"{port.service} {port.banner or ''}".lower()
        for token, name in signatures.items():
            if token in haystack:
                detected.append(name)

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                if str(key).lower() in {"technology", "technologies", "framework", "server"}:
                    walk(child)
                elif isinstance(child, (dict, list, tuple, set)):
                    walk(child)
        elif isinstance(value, (list, tuple, set)):
            for child in value:
                walk(child)
        elif isinstance(value, str):
            lower = value.lower()
            for token, name in signatures.items():
                if token in lower:
                    detected.append(name)

    walk(plugin_results)
    return _unique(detected)


def build_attack_surface(result: ScanResult) -> AttackSurface:
    open_ports = result.open_ports
    services = _unique(port.service for port in open_ports if port.service != "unknown")
    findings: list[SurfaceFinding] = []

    for service in services:
        if service in RISKY_SERVICES:
            severity, detail = RISKY_SERVICES[service]
            findings.append(
                SurfaceFinding(
                    severity=severity,
                    title=f"Exposed {service} service",
                    detail=detail,
                    evidence=", ".join(
                        f"{p.port}/tcp" for p in open_ports if p.service == service
                    ),
                    recommendation="Confirm business need, patch the service, and restrict access to trusted sources.",
                )
            )

    if len(open_ports) >= 20:
        findings.append(
            SurfaceFinding(
                severity="high",
                title="Broad TCP exposure",
                detail=f"{len(open_ports)} open TCP ports were observed in the selected scan range.",
                evidence=", ".join(str(p.port) for p in open_ports[:25]),
                recommendation="Reduce externally reachable services to the minimum required set.",
            )
        )
    elif len(open_ports) >= 8:
        findings.append(
            SurfaceFinding(
                severity="medium",
                title="Expanded TCP exposure",
                detail=f"{len(open_ports)} open TCP ports were observed.",
                evidence=", ".join(str(p.port) for p in open_ports),
                recommendation="Review each exposed service and document its business purpose.",
            )
        )

    if any(service in REMOTE_ADMIN_SERVICES for service in services):
        findings.append(
            SurfaceFinding(
                severity="low",
                title="Remote administration surface present",
                detail="At least one remote administration service is reachable.",
                evidence=", ".join(sorted(set(services) & REMOTE_ADMIN_SERVICES)),
                recommendation="Use source allowlists, MFA, strong credentials, and current software versions.",
            )
        )

    if any(service in WEB_SERVICES for service in services):
        findings.append(
            SurfaceFinding(
                severity="info",
                title="Web application surface detected",
                detail="A web-facing service is reachable and can be evaluated by future HTTP, TLS, and header modules.",
                evidence=", ".join(
                    f"{p.port}/tcp" for p in open_ports if p.service in WEB_SERVICES
                ),
                recommendation="Run web technology, security-header, and TLS inspection modules.",
            )
        )

    if any(service in DATABASE_SERVICES for service in services):
        findings.append(
            SurfaceFinding(
                severity="high",
                title="Database service reachable",
                detail="A database-oriented service is exposed in the selected assessment scope.",
                evidence=", ".join(sorted(set(services) & DATABASE_SERVICES)),
                recommendation="Keep databases on private networks and permit only required application hosts.",
            )
        )

    if not open_ports:
        findings.append(
            SurfaceFinding(
                severity="info",
                title="No open TCP ports observed",
                detail="No open ports were found in the selected range. This does not prove the host has no exposure.",
                recommendation="Consider a wider authorized profile or additional protocol-specific checks.",
            )
        )

    raw_risk = sum(SEVERITY_WEIGHTS.get(item.severity, 0) for item in findings)
    risk_score = min(100, raw_risk)
    if risk_score >= 75:
        risk_level = "CRITICAL"
    elif risk_score >= 50:
        risk_level = "HIGH"
    elif risk_score >= 25:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    categories = {
        "network": len(open_ports),
        "web": sum(1 for service in services if service in WEB_SERVICES),
        "remote_admin": sum(1 for service in services if service in REMOTE_ADMIN_SERVICES),
        "databases": sum(1 for service in services if service in DATABASE_SERVICES),
    }

    return AttackSurface(
        target=result.target,
        ip=result.ip,
        hostname=result.hostname,
        operation_id=result.operation_id,
        profile=result.profile,
        open_ports=[port.port for port in open_ports],
        services=services,
        technologies=_detect_technologies(open_ports, result.plugin_results),
        findings=findings,
        exposure_categories=categories,
        risk_score=risk_score,
        risk_level=risk_level,
        attack_surface_score=max(0, 100 - risk_score),
    )
