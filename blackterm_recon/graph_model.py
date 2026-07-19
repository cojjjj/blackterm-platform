from __future__ import annotations

from dataclasses import dataclass
from math import cos, pi, sin
from typing import Any, Iterable


KIND_RINGS = {
    "CASE": 0,
    "SCAN": 1,
    "TARGET": 2,
    "DOMAIN": 2,
    "IP": 2,
    "SERVICE": 3,
    "PORT": 3,
    "DNS": 3,
    "WHOIS": 3,
    "SSL": 3,
    "TLS": 3,
    "HEADERS": 3,
    "SCREENSHOT": 3,
    "FILE": 3,
    "LOG": 3,
    "OBSERVATION": 3,
    "AI": 4,
    "FINDING": 4,
    "OTHER": 4,
}


@dataclass(frozen=True, slots=True)
class GraphNode:
    node_id: str
    kind: str
    label: str
    detail: str
    risk: int
    x: float
    y: float


@dataclass(frozen=True, slots=True)
class GraphEdge:
    source: str
    target: str
    relationship: str
    confidence: int


@dataclass(frozen=True, slots=True)
class GraphSnapshot:
    nodes: tuple[GraphNode, ...]
    edges: tuple[GraphEdge, ...]


def _value(item: Any, key: str, default: Any = None) -> Any:
    if isinstance(item, dict):
        return item.get(key, default)
    return getattr(item, key, default)


def build_graph_snapshot(
    nodes: Iterable[Any],
    edges: Iterable[Any],
    *,
    ring_spacing: float = 225.0,
) -> GraphSnapshot:
    """Convert correlation objects into a stable radial graph layout."""
    raw_nodes = list(nodes)
    raw_edges = list(edges)
    if not raw_nodes:
        return GraphSnapshot((), ())

    grouped: dict[int, list[Any]] = {}
    for node in raw_nodes:
        kind = str(_value(node, "kind", "OTHER") or "OTHER").upper()
        ring = KIND_RINGS.get(kind, 4)
        grouped.setdefault(ring, []).append(node)

    positioned: list[GraphNode] = []
    for ring in sorted(grouped):
        members = sorted(
            grouped[ring],
            key=lambda item: (
                str(_value(item, "kind", "")),
                str(_value(item, "label", "")),
                str(_value(item, "node_id", "")),
            ),
        )
        if ring == 0:
            for index, item in enumerate(members):
                positioned.append(
                    GraphNode(
                        node_id=str(_value(item, "node_id", f"root:{index}")),
                        kind=str(_value(item, "kind", "CASE")).upper(),
                        label=str(_value(item, "label", "Investigation")),
                        detail=str(_value(item, "detail", "")),
                        risk=int(_value(item, "risk", 0) or 0),
                        x=(index - (len(members) - 1) / 2) * 180.0,
                        y=0.0,
                    )
                )
            continue

        radius = ring * ring_spacing
        count = max(1, len(members))
        start_angle = -pi / 2
        for index, item in enumerate(members):
            angle = start_angle + (2 * pi * index / count)
            positioned.append(
                GraphNode(
                    node_id=str(_value(item, "node_id", f"node:{ring}:{index}")),
                    kind=str(_value(item, "kind", "OTHER")).upper(),
                    label=str(_value(item, "label", "Unknown")),
                    detail=str(_value(item, "detail", "")),
                    risk=int(_value(item, "risk", 0) or 0),
                    x=cos(angle) * radius,
                    y=sin(angle) * radius,
                )
            )

    valid_ids = {node.node_id for node in positioned}
    normalized_edges: list[GraphEdge] = []
    seen: set[tuple[str, str, str]] = set()
    for edge in raw_edges:
        source = str(_value(edge, "source", ""))
        target = str(_value(edge, "target", ""))
        relationship = str(_value(edge, "relationship", "related to") or "related to")
        key = (source, target, relationship)
        if source not in valid_ids or target not in valid_ids or key in seen:
            continue
        seen.add(key)
        normalized_edges.append(
            GraphEdge(
                source=source,
                target=target,
                relationship=relationship,
                confidence=max(0, min(100, int(_value(edge, "confidence", 70) or 70))),
            )
        )

    return GraphSnapshot(tuple(positioned), tuple(normalized_edges))
