from __future__ import annotations

import ipaddress
import json
import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Iterable

from .correlation_engine import CorrelationEdge, CorrelationNode

_DOMAIN_RE = re.compile(r"\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}\b", re.I)
_ASN_RE = re.compile(r"\bAS\d{1,10}\b", re.I)
_CERT_RE = re.compile(r"\b(?:sha256|fingerprint|serial)\s*[:=]\s*([A-Fa-f0-9:]{12,})", re.I)
_TECH_KEYS = {"technology", "technologies", "product", "server", "framework", "cms"}
_ORG_KEYS = {"organization", "org", "isp", "network", "provider", "owner"}
_ASN_KEYS = {"asn", "as_number", "autonomous_system"}
_DOMAIN_KEYS = {"domain", "hostname", "host", "fqdn"}
_IP_KEYS = {"ip", "address", "resolved_ip"}
_CERT_KEYS = {"certificate", "fingerprint", "serial_number", "sha256"}


@dataclass(frozen=True, slots=True)
class RelationshipGraphReport:
    nodes: tuple[CorrelationNode, ...]
    edges: tuple[CorrelationEdge, ...]
    level: str = "GLOBAL"


@dataclass(frozen=True, slots=True)
class GraphStats:
    cases: int
    entities: int
    relationships: int
    shared_entities: int


def _safe_json(value: str) -> Any:
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return None


def _is_ip(value: str) -> bool:
    try:
        ipaddress.ip_address(value.strip())
        return True
    except ValueError:
        return False


def _clean(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (str, int, float)):
        return str(value).strip()
    return ""


def _walk_entities(value: Any, key: str = "") -> Iterable[tuple[str, str]]:
    if isinstance(value, dict):
        for child_key, child in value.items():
            yield from _walk_entities(child, str(child_key).lower())
        return
    if isinstance(value, list):
        for child in value:
            yield from _walk_entities(child, key)
        return
    text = _clean(value)
    if not text or len(text) > 500:
        return
    lower_key = key.lower()
    if lower_key in _IP_KEYS and _is_ip(text):
        yield "IP", text
    elif lower_key in _DOMAIN_KEYS and _DOMAIN_RE.fullmatch(text.lower()):
        yield "DOMAIN", text.lower()
    elif lower_key in _ASN_KEYS:
        match = _ASN_RE.search(text)
        if match:
            yield "ASN", match.group(0).upper()
    elif lower_key in _ORG_KEYS and 2 <= len(text) <= 120:
        yield "ORGANIZATION", text
    elif lower_key in _TECH_KEYS and 1 < len(text) <= 100:
        yield "TECHNOLOGY", text
    elif lower_key in _CERT_KEYS and 6 < len(text) <= 180:
        yield "CERTIFICATE", text


def _text_entities(text: str) -> Iterable[tuple[str, str]]:
    for domain in _DOMAIN_RE.findall(text or ""):
        yield "DOMAIN", domain.lower()
    for token in re.findall(r"(?<![\w.])(?:\d{1,3}\.){3}\d{1,3}(?![\w.])", text or ""):
        if _is_ip(token):
            yield "IP", token
    for asn in _ASN_RE.findall(text or ""):
        yield "ASN", asn.upper()
    for cert in _CERT_RE.findall(text or ""):
        yield "CERTIFICATE", cert.replace(":", "").upper()


def _entity_id(kind: str, value: str) -> str:
    return f"entity:{kind.lower()}:{value.strip().lower()}"


def build_relationship_graph(repository: Any, query: str = "") -> tuple[RelationshipGraphReport, GraphStats]:
    query_lower = query.strip().lower()
    all_cases = list(repository.list_cases() or [])
    cases = []
    for case in all_cases:
        if not query_lower:
            cases.append(case)
            continue
        haystack = " ".join(str(case.get(k, "")) for k in ("id", "name", "description", "status")).lower()
        if query_lower in haystack:
            cases.append(case)
            continue
        evidence = repository.case_evidence(int(case["id"])) or []
        if any(query_lower in (str(item.get("title", "")) + " " + str(item.get("content", ""))).lower() for item in evidence):
            cases.append(case)

    nodes: dict[str, CorrelationNode] = {}
    edges: dict[tuple[str, str, str], CorrelationEdge] = {}
    entity_cases: dict[str, set[int]] = defaultdict(set)

    def add_node(node_id: str, kind: str, label: str, detail: str = "", risk: int = 0):
        existing = nodes.get(node_id)
        if existing and len(existing.detail) >= len(detail):
            return
        nodes[node_id] = CorrelationNode(node_id, kind, label, detail, risk)

    def add_edge(source: str, target: str, relationship: str, confidence: int = 80):
        edges[(source, target, relationship)] = CorrelationEdge(source, target, relationship, confidence)

    for case in cases:
        case_id = int(case["id"])
        case_node = f"case:{case_id}"
        add_node(case_node, "CASE", f"Case #{case_id}", f"{case.get('name', '')} // {case.get('status', '')}")

        scans = repository.case_scans(case_id) or []
        for scan in scans:
            target = _clean(scan.get("target"))
            ip = _clean(scan.get("ip"))
            for kind, value in (("TARGET", target), ("IP", ip)):
                if not value:
                    continue
                entity_kind = "DOMAIN" if kind == "TARGET" and _DOMAIN_RE.fullmatch(value.lower()) else kind
                node_id = _entity_id(entity_kind, value)
                add_node(node_id, entity_kind, value, f"Observed in scan #{scan.get('id', '?')}")
                add_edge(case_node, node_id, "contains", 96)
                entity_cases[node_id].add(case_id)
            if target and ip:
                add_edge(_entity_id("DOMAIN" if _DOMAIN_RE.fullmatch(target.lower()) else "TARGET", target), _entity_id("IP", ip), "resolves to", 92)

        for item in repository.case_evidence(case_id) or []:
            evidence_type = _clean(item.get("evidence_type")).upper() or "EVIDENCE"
            title = _clean(item.get("title")) or "Evidence"
            source = _clean(item.get("source"))
            content = _clean(item.get("content"))
            evidence_id = f"evidence:{item.get('id', case_id)}"
            add_node(evidence_id, evidence_type, title, source, 2)
            add_edge(case_node, evidence_id, "supported by", 82)

            discovered: set[tuple[str, str]] = set()
            payload = _safe_json(content)
            if payload is not None:
                discovered.update(_walk_entities(payload))
            discovered.update(_text_entities(" ".join((title, source, content))))

            for kind, value in discovered:
                if not value:
                    continue
                node_id = _entity_id(kind, value)
                add_node(node_id, kind, value, f"Extracted from {title}")
                add_edge(evidence_id, node_id, "identifies", 84)
                add_edge(case_node, node_id, "correlates", 76)
                entity_cases[node_id].add(case_id)

    shared_count = 0
    for entity_id, linked_cases in entity_cases.items():
        if len(linked_cases) < 2:
            continue
        shared_count += 1
        ordered = sorted(linked_cases)
        for left, right in zip(ordered, ordered[1:]):
            add_edge(f"case:{left}", f"case:{right}", f"share {nodes[entity_id].kind.lower()}", 88)

    report = RelationshipGraphReport(tuple(nodes.values()), tuple(edges.values()))
    stats = GraphStats(
        cases=len(cases),
        entities=sum(1 for node in nodes.values() if node.kind != "CASE"),
        relationships=len(edges),
        shared_entities=shared_count,
    )
    return report, stats
