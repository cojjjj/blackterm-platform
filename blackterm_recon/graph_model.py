from __future__ import annotations

from dataclasses import dataclass
from math import cos, pi, sin, ceil, sqrt
from typing import Any, Iterable


KIND_RINGS = {
    "CASE": 0,
    "SCAN": 1,
    "TARGET": 2,
    "DOMAIN": 2,
    "IP": 2,
    "ORGANIZATION": 2,
    "ASN": 2,
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
    "TECHNOLOGY": 3,
    "CERTIFICATE": 3,
    "OSINT": 3,
    "THREAT_INTELLIGENCE": 3,
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
    layout: str = "network",
) -> GraphSnapshot:
    """Convert correlation objects into a stable, readable graph layout.

    Layouts:
    - ``network``: radial overview compatible with earlier BLACKTERM releases.
    - ``cluster``: entity types occupy separate columns and compact rows.
    - ``tree``: case roots flow left-to-right through relationship depth.
    - ``explore``: case-first radial layout for progressive node expansion.
    """
    raw_nodes = list(nodes)
    raw_edges = list(edges)
    if not raw_nodes:
        return GraphSnapshot((), ())

    def make(item: Any, x: float, y: float, index: int = 0) -> GraphNode:
        return GraphNode(
            node_id=str(_value(item, "node_id", f"node:{index}")),
            kind=str(_value(item, "kind", "OTHER") or "OTHER").upper(),
            label=str(_value(item, "label", "Unknown")),
            detail=str(_value(item, "detail", "")),
            risk=int(_value(item, "risk", 0) or 0),
            x=float(x),
            y=float(y),
        )

    layout = (layout or "network").lower()
    positioned: list[GraphNode] = []


    if layout == "explore":
        by_id = {str(_value(n, "node_id", "")): n for n in raw_nodes}
        adjacency: dict[str, set[str]] = {node_id: set() for node_id in by_id}
        for edge in raw_edges:
            source, target = str(_value(edge, "source", "")), str(_value(edge, "target", ""))
            if source in adjacency and target in adjacency:
                adjacency[source].add(target)
                adjacency[target].add(source)

        roots = sorted(
            [node_id for node_id, item in by_id.items() if str(_value(item, "kind", "")).upper() == "CASE"]
        ) or [next(iter(by_id))]
        root_gap = 720.0
        root_positions: dict[str, tuple[float, float]] = {}
        for index, root in enumerate(roots):
            x = (index - (len(roots) - 1) / 2) * root_gap
            root_positions[root] = (x, 0.0)
            positioned.append(make(by_id[root], x, 0.0, index))

        assigned = set(roots)
        kind_angle = {
            "TARGET": -2.55, "DOMAIN": -2.15, "IP": -1.45, "ASN": -0.75,
            "ORGANIZATION": -0.15, "CERTIFICATE": 0.55, "TECHNOLOGY": 1.05,
            "OSINT": 1.55, "THREAT_INTELLIGENCE": 2.05, "EVIDENCE": 2.55,
        }
        for root_index, root in enumerate(roots):
            members = [node_id for node_id in adjacency.get(root, ()) if node_id not in assigned]
            members.sort(key=lambda node_id: (str(_value(by_id[node_id], "kind", "")), str(_value(by_id[node_id], "label", ""))))
            grouped_members: dict[str, list[str]] = {}
            for node_id in members:
                kind = str(_value(by_id[node_id], "kind", "OTHER") or "OTHER").upper()
                grouped_members.setdefault(kind, []).append(node_id)
            center_x, center_y = root_positions[root]
            for group_index, (kind, node_ids) in enumerate(sorted(grouped_members.items())):
                base_angle = kind_angle.get(kind, -2.8 + group_index * 0.55)
                radius = 190.0 + min(170.0, len(node_ids) * 8.0)
                spread = min(1.15, 0.18 * max(1, len(node_ids) - 1))
                for item_index, node_id in enumerate(node_ids):
                    offset = 0.0 if len(node_ids) == 1 else -spread / 2 + spread * item_index / (len(node_ids) - 1)
                    angle = base_angle + offset
                    x = center_x + cos(angle) * radius
                    y = center_y + sin(angle) * radius
                    positioned.append(make(by_id[node_id], x, y, item_index))
                    assigned.add(node_id)

        # Any remaining nodes are secondary context. Place them beneath the nearest
        # already-positioned neighbour, keeping the initial explorer readable.
        position_index = {node.node_id: (node.x, node.y) for node in positioned}
        remaining = [node_id for node_id in by_id if node_id not in assigned]
        for index, node_id in enumerate(remaining):
            anchors = [neighbor for neighbor in adjacency.get(node_id, ()) if neighbor in position_index]
            if anchors:
                anchor_x, anchor_y = position_index[anchors[0]]
                angle = (index % 8) * (2 * pi / 8)
                ring = 150.0 + (index // 8) * 95.0
                x, y = anchor_x + cos(angle) * ring, anchor_y + sin(angle) * ring
            else:
                x, y = (index % 8) * 150.0, 520.0 + (index // 8) * 130.0
            positioned.append(make(by_id[node_id], x, y, index))
            position_index[node_id] = (x, y)

    elif layout == "cluster":
        kinds: dict[str, list[Any]] = {}
        for item in raw_nodes:
            kind = str(_value(item, "kind", "OTHER") or "OTHER").upper()
            kinds.setdefault(kind, []).append(item)
        order = [
            "CASE", "DOMAIN", "TARGET", "IP", "ASN", "ORGANIZATION",
            "CERTIFICATE", "TECHNOLOGY", "OSINT", "THREAT_INTELLIGENCE",
            "DNS", "TLS", "WHOIS", "SERVICE", "PORT", "EVIDENCE", "OTHER",
        ]
        ordered_kinds = sorted(kinds, key=lambda k: (order.index(k) if k in order else len(order), k))

        # Place entity kinds in a wide dashboard-style matrix rather than one
        # extremely tall column per kind. Large graphs therefore retain a
        # useful aspect ratio when fitted into the viewport.
        cluster_columns = min(4, max(1, ceil(sqrt(len(ordered_kinds) * 1.55))))
        cluster_gap_x, cluster_gap_y = 620.0, 500.0
        node_gap_x, node_gap_y = 118.0, 110.0
        cluster_rows = ceil(len(ordered_kinds) / cluster_columns)
        total_width = max(0, cluster_columns - 1) * cluster_gap_x
        total_height = max(0, cluster_rows - 1) * cluster_gap_y

        for cluster_index, kind in enumerate(ordered_kinds):
            members = sorted(
                kinds[kind],
                key=lambda i: (str(_value(i, "label", "")), str(_value(i, "node_id", ""))),
            )
            cluster_col = cluster_index % cluster_columns
            cluster_row = cluster_index // cluster_columns
            # A small row-dependent horizontal stagger keeps each entity
            # kind on a distinct axis while preserving the wide matrix.
            center_x = cluster_col * cluster_gap_x - total_width / 2 + cluster_row * 54.0
            center_y = cluster_row * cluster_gap_y - total_height / 2

            # Dense entity groups use a compact local grid. Cases remain larger
            # and receive fewer columns so they are easy to identify.
            local_columns = max(1, min(7 if kind != "CASE" else 4, ceil(sqrt(len(members) * 1.35))))
            local_rows = ceil(len(members) / local_columns)
            local_width = max(0, local_columns - 1) * node_gap_x
            local_height = max(0, local_rows - 1) * node_gap_y
            for member_index, item in enumerate(members):
                local_col = member_index % local_columns
                local_row = member_index // local_columns
                x = center_x + local_col * node_gap_x - local_width / 2
                y = center_y + local_row * node_gap_y - local_height / 2
                positioned.append(make(item, x, y, member_index))

    elif layout == "tree":
        by_id = {str(_value(n, "node_id", "")): n for n in raw_nodes}
        adjacency: dict[str, set[str]] = {node_id: set() for node_id in by_id}
        for edge in raw_edges:
            source, target = str(_value(edge, "source", "")), str(_value(edge, "target", ""))
            if source in adjacency and target in adjacency:
                adjacency[source].add(target)
                adjacency[target].add(source)
        roots = sorted(
            [node_id for node_id, item in by_id.items() if str(_value(item, "kind", "")).upper() == "CASE"]
        ) or [next(iter(by_id))]
        depth: dict[str, int] = {}
        queue = [(root, 0) for root in roots]
        for root in roots:
            depth[root] = 0
        while queue:
            node_id, current = queue.pop(0)
            for neighbor in sorted(adjacency.get(node_id, ())):
                if neighbor not in depth:
                    depth[neighbor] = current + 1
                    queue.append((neighbor, current + 1))
        fallback = max(depth.values(), default=0) + 1
        levels: dict[int, list[Any]] = {}
        for node_id, item in by_id.items():
            levels.setdefault(depth.get(node_id, fallback), []).append(item)
        column_gap, row_gap = 285.0, 118.0
        for level in sorted(levels):
            members = sorted(levels[level], key=lambda i: (str(_value(i, "kind", "")), str(_value(i, "label", ""))))
            y0 = -((len(members) - 1) * row_gap) / 2
            for row, item in enumerate(members):
                positioned.append(make(item, level * column_gap, y0 + row * row_gap, row))

    else:
        grouped: dict[int, list[Any]] = {}
        for node in raw_nodes:
            kind = str(_value(node, "kind", "OTHER") or "OTHER").upper()
            grouped.setdefault(KIND_RINGS.get(kind, 4), []).append(node)
        for ring in sorted(grouped):
            members = sorted(grouped[ring], key=lambda item: (str(_value(item, "kind", "")), str(_value(item, "label", "")), str(_value(item, "node_id", ""))))
            if ring == 0:
                for index, item in enumerate(members):
                    positioned.append(make(item, (index - (len(members) - 1) / 2) * 180.0, 0.0, index))
                continue
            # Increase radius when a ring is crowded so labels and nodes do not form a solid circle.
            radius = max(ring * ring_spacing, (len(members) * 75.0) / (2 * pi))
            for index, item in enumerate(members):
                angle = -pi / 2 + (2 * pi * index / max(1, len(members)))
                positioned.append(make(item, cos(angle) * radius, sin(angle) * radius, index))

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
        normalized_edges.append(GraphEdge(
            source=source,
            target=target,
            relationship=relationship,
            confidence=max(0, min(100, int(_value(edge, "confidence", 70) or 70))),
        ))
    return GraphSnapshot(tuple(positioned), tuple(normalized_edges))

