from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any, Iterable


HIGH_SIGNAL_PORTS = {
    21: ("FTP", 12, "unencrypted file transfer exposure"),
    23: ("Telnet", 25, "unencrypted remote administration exposure"),
    139: ("NetBIOS", 10, "legacy Windows file-sharing exposure"),
    445: ("SMB", 20, "Windows file-sharing exposure"),
    3389: ("RDP", 20, "remote desktop exposure"),
    5900: ("VNC", 18, "remote console exposure"),
}

EVIDENCE_WEIGHTS = {
    "WHOIS": 4,
    "DNS": 5,
    "HEADERS": 5,
    "SSL": 7,
    "TLS": 7,
    "SCREENSHOT": 3,
    "AI": 2,
    "FILE": 3,
    "OBSERVATION": 3,
    "LOG": 5,
}


@dataclass(frozen=True, slots=True)
class CorrelationNode:
    node_id: str
    kind: str
    label: str
    detail: str = ""
    risk: int = 0


@dataclass(frozen=True, slots=True)
class CorrelationEdge:
    source: str
    target: str
    relationship: str
    confidence: int = 70


@dataclass(frozen=True, slots=True)
class CorrelationReport:
    case_id: int
    score: int
    level: str
    confidence: int
    summary: str
    patterns: tuple[str, ...]
    recommendations: tuple[str, ...]
    nodes: tuple[CorrelationNode, ...]
    edges: tuple[CorrelationEdge, ...]

    def to_text(self) -> str:
        patterns = "\n".join(f"- {item}" for item in self.patterns) or "- No multi-source pattern was confirmed."
        recommendations = "\n".join(
            f"{index}. {item}" for index, item in enumerate(self.recommendations, 1)
        ) or "1. Continue collecting evidence and validate the target scope."
        return (
            "BLACKTERM INTELLIGENCE CORRELATION\n\n"
            f"CASE: #{self.case_id}\n"
            f"PRIORITY: {self.level}\n"
            f"CORRELATION SCORE: {self.score}/100\n"
            f"CONFIDENCE: {self.confidence}%\n"
            f"RELATIONSHIPS: {len(self.edges)}\n\n"
            f"INTELLIGENCE SUMMARY\n{self.summary}\n\n"
            f"CORRELATED PATTERNS\n{patterns}\n\n"
            f"RECOMMENDED NEXT STEPS\n{recommendations}\n\n"
            "Correlation is advisory and should be validated by an authorized analyst."
        )


def _level(score: int) -> str:
    if score >= 80:
        return "CRITICAL"
    if score >= 55:
        return "HIGH"
    if score >= 30:
        return "MODERATE"
    return "LOW"


def _value(item: Any, key: str, default: Any = None) -> Any:
    if isinstance(item, dict):
        return item.get(key, default)
    return getattr(item, key, default)


def _iter_ports(result: Any) -> Iterable[Any]:
    return list(_value(result, "open_ports", []) or [])


def correlate_case(repository: Any, case_id: int) -> CorrelationReport:
    scans = list(repository.case_scans(case_id) or [])
    evidence = list(repository.case_evidence(case_id) or [])
    notes = list(repository.case_notes(case_id) or [])

    nodes: list[CorrelationNode] = [
        CorrelationNode(f"case:{case_id}", "CASE", f"Case #{case_id}", "Investigation root")
    ]
    edges: list[CorrelationEdge] = []
    patterns: list[str] = []
    recommendations: list[str] = []
    port_hosts: dict[int, set[str]] = defaultdict(set)
    port_counts: Counter[int] = Counter()
    service_counts: Counter[str] = Counter()
    targets: set[str] = set()
    score = 5

    for scan in scans:
        scan_id = int(_value(scan, "id", 0) or 0)
        result = repository.get(scan_id) if scan_id else None
        target = str(_value(scan, "target", _value(result, "target", "unknown")) or "unknown")
        ip = str(_value(scan, "ip", _value(result, "ip", "")) or "")
        targets.add(target)
        scan_node = f"scan:{scan_id}"
        nodes.append(CorrelationNode(scan_node, "SCAN", f"Scan #{scan_id}", f"{target} {ip}".strip()))
        edges.append(CorrelationEdge(f"case:{case_id}", scan_node, "contains", 100))

        target_node = f"target:{target}"
        nodes.append(CorrelationNode(target_node, "TARGET", target, ip))
        edges.append(CorrelationEdge(scan_node, target_node, "observed", 95))

        for port_item in _iter_ports(result):
            port = int(_value(port_item, "port", 0) or 0)
            if not port:
                continue
            service = str(_value(port_item, "service", "unknown") or "unknown").lower()
            port_hosts[port].add(target)
            port_counts[port] += 1
            service_counts[service] += 1
            weight = HIGH_SIGNAL_PORTS.get(port, (service.upper(), 2, "service exposure"))[1]
            port_node = f"port:{target}:{port}"
            nodes.append(CorrelationNode(port_node, "SERVICE", f"TCP/{port} {service}", target, weight))
            edges.append(CorrelationEdge(target_node, port_node, "exposes", 90))
            score += min(weight, 12)

    evidence_types: Counter[str] = Counter()
    for item in evidence:
        evidence_id = _value(item, "id", len(nodes))
        evidence_type = str(_value(item, "evidence_type", "OTHER") or "OTHER").upper()
        title = str(_value(item, "title", "Evidence") or "Evidence")
        source = str(_value(item, "source", _value(item, "file_path", "")) or "")
        evidence_types[evidence_type] += 1
        evidence_node = f"evidence:{evidence_id}"
        nodes.append(CorrelationNode(evidence_node, evidence_type, title, source, EVIDENCE_WEIGHTS.get(evidence_type, 2)))
        edges.append(CorrelationEdge(f"case:{case_id}", evidence_node, "supports", 82))
        score += EVIDENCE_WEIGHTS.get(evidence_type, 2)

        source_lower = source.lower()
        title_lower = title.lower()
        for target in targets:
            if target.lower() in source_lower or target.lower() in title_lower:
                edges.append(CorrelationEdge(evidence_node, f"target:{target}", "references", 88))

    if len(scans) > 1:
        patterns.append(f"The investigation correlates {len(scans)} scans instead of relying on a single observation.")
        score += min(12, len(scans) * 3)

    repeated_ports = sorted(port for port, count in port_counts.items() if count > 1)
    if repeated_ports:
        display = ", ".join(f"TCP/{port}" for port in repeated_ports[:8])
        patterns.append(f"Repeated service exposure was observed across targets or scans: {display}.")
        recommendations.append("Compare repeated services across scan times and validate whether exposure is intentional.")
        score += min(15, len(repeated_ports) * 4)

    sensitive = sorted(port for port in port_hosts if port in HIGH_SIGNAL_PORTS)
    if sensitive:
        names = [HIGH_SIGNAL_PORTS[port][0] for port in sensitive]
        patterns.append(f"High-signal remote or legacy services are present: {', '.join(names)}.")
        recommendations.append("Prioritize validation of remote administration and legacy service controls.")

    if len(evidence_types) >= 3:
        patterns.append(
            "Multiple evidence classes support the case: "
            + ", ".join(f"{kind} ({count})" for kind, count in evidence_types.most_common())
            + "."
        )
        score += min(12, len(evidence_types) * 3)

    if notes:
        patterns.append(f"Analyst context is available through {len(notes)} operator note(s).")
        score += min(8, len(notes))

    if service_counts:
        common_service, count = service_counts.most_common(1)[0]
        if count > 1:
            patterns.append(f"{common_service.upper()} is the most repeated observed service ({count} observations).")

    if not recommendations:
        recommendations.append("Validate each correlated relationship against the approved investigation scope.")
    recommendations.append("Re-run relevant scans later and compare changes in exposed services and supporting evidence.")
    recommendations.append("Preserve high-value evidence with source, timestamp, and integrity hash information.")

    score = max(5, min(100, score))
    source_count = len(scans) + len(evidence) + len(notes)
    confidence = max(45, min(98, 48 + source_count * 4 + len(patterns) * 5))
    level = _level(score)

    if patterns:
        summary = (
            f"Case #{case_id} contains {len(scans)} scan(s), {len(evidence)} evidence item(s), "
            f"and {len(notes)} analyst note(s). BLACKTERM identified {len(patterns)} correlated "
            f"pattern(s) with {confidence}% confidence and assigned {level} priority."
        )
    else:
        summary = (
            f"Case #{case_id} does not yet contain enough independent signals for strong correlation. "
            "Additional scans, evidence, or analyst context will increase confidence."
        )

    # Remove duplicate nodes/edges while preserving order.
    unique_nodes = tuple({node.node_id: node for node in nodes}.values())
    unique_edges = tuple(dict.fromkeys(edges))
    return CorrelationReport(
        case_id=case_id,
        score=score,
        level=level,
        confidence=confidence,
        summary=summary,
        patterns=tuple(dict.fromkeys(patterns)),
        recommendations=tuple(dict.fromkeys(recommendations)),
        nodes=unique_nodes,
        edges=unique_edges,
    )
