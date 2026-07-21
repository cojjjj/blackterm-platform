from __future__ import annotations

from dataclasses import dataclass, field
from collections import defaultdict, deque

from PySide6.QtCore import QPointF, QRectF


@dataclass(slots=True)
class GraphNodeSpec:
    node_id: str
    kind: str
    title: str
    subtitle: str = ""
    accent: str = "#31b7ff"
    payload: object | None = None
    width: float = 188.0
    height: float = 68.0


@dataclass(slots=True)
class GraphEdgeSpec:
    source: str
    target: str
    accent: str = "#244667"
    width: float = 1.5


@dataclass(slots=True)
class GraphLayout:
    positions: dict[str, QPointF] = field(default_factory=dict)
    bounds: QRectF = field(default_factory=QRectF)
    depth: dict[str, int] = field(default_factory=dict)


class HierarchicalGraphEngine:
    """Reusable layered-tree layout used by attack surface and future graph pages."""

    def __init__(
        self,
        *,
        horizontal_gap: float = 48.0,
        vertical_gap: float = 105.0,
        margin: float = 70.0,
        minimum_width: float = 1050.0,
        minimum_height: float = 520.0,
    ) -> None:
        self.horizontal_gap = horizontal_gap
        self.vertical_gap = vertical_gap
        self.margin = margin
        self.minimum_width = minimum_width
        self.minimum_height = minimum_height

    def layout(
        self,
        nodes: list[GraphNodeSpec],
        edges: list[GraphEdgeSpec],
        root_id: str,
        collapsed: set[str] | None = None,
    ) -> GraphLayout:
        collapsed = collapsed or set()
        by_id = {node.node_id: node for node in nodes}
        children: dict[str, list[str]] = defaultdict(list)
        parents: dict[str, str] = {}
        for edge in edges:
            if edge.source in by_id and edge.target in by_id:
                children[edge.source].append(edge.target)
                parents[edge.target] = edge.source

        visible: set[str] = set()
        depth: dict[str, int] = {}
        queue: deque[tuple[str, int]] = deque([(root_id, 0)])
        while queue:
            node_id, level = queue.popleft()
            if node_id in visible or node_id not in by_id:
                continue
            visible.add(node_id)
            depth[node_id] = level
            if node_id in collapsed:
                continue
            for child in children.get(node_id, []):
                queue.append((child, level + 1))

        # Include disconnected nodes at the final level instead of silently losing telemetry.
        max_depth = max(depth.values(), default=0)
        for node in nodes:
            if node.node_id not in visible:
                visible.add(node.node_id)
                max_depth += 1
                depth[node.node_id] = max_depth

        leaf_width: dict[str, float] = {}

        def subtree_width(node_id: str) -> float:
            node = by_id[node_id]
            visible_children = [child for child in children.get(node_id, []) if child in visible]
            if not visible_children or node_id in collapsed:
                width = node.width
            else:
                child_widths = [subtree_width(child) for child in visible_children]
                width = max(node.width, sum(child_widths) + self.horizontal_gap * (len(child_widths) - 1))
            leaf_width[node_id] = width
            return width

        root_width = subtree_width(root_id) if root_id in by_id else self.minimum_width
        canvas_width = max(self.minimum_width, root_width + self.margin * 2)
        positions: dict[str, QPointF] = {}

        def place(node_id: str, left: float, top: float) -> None:
            node = by_id[node_id]
            width = leaf_width.get(node_id, node.width)
            x = left + (width - node.width) / 2
            positions[node_id] = QPointF(x, top)
            visible_children = [child for child in children.get(node_id, []) if child in visible]
            if not visible_children or node_id in collapsed:
                return
            cursor = left
            child_top = top + node.height + self.vertical_gap
            for child in visible_children:
                child_width = leaf_width[child]
                place(child, cursor, child_top)
                cursor += child_width + self.horizontal_gap

        if root_id in by_id:
            place(root_id, (canvas_width - root_width) / 2, self.margin)

        # Place disconnected nodes in a clean final row.
        disconnected = [node for node in nodes if node.node_id in visible and node.node_id not in positions]
        if disconnected:
            row_y = max((point.y() + by_id[node_id].height for node_id, point in positions.items()), default=0) + self.vertical_gap
            total = sum(node.width for node in disconnected) + self.horizontal_gap * max(0, len(disconnected) - 1)
            cursor = max(self.margin, (canvas_width - total) / 2)
            for node in disconnected:
                positions[node.node_id] = QPointF(cursor, row_y)
                cursor += node.width + self.horizontal_gap

        max_bottom = max(
            (point.y() + by_id[node_id].height for node_id, point in positions.items()),
            default=self.minimum_height,
        )
        bounds = QRectF(0, 0, canvas_width, max(self.minimum_height, max_bottom + self.margin))
        return GraphLayout(positions=positions, bounds=bounds, depth=depth)

    @staticmethod
    def ancestry(node_id: str, edges: list[GraphEdgeSpec]) -> set[str]:
        parent = {edge.target: edge.source for edge in edges}
        result = {node_id}
        current = node_id
        while current in parent:
            current = parent[current]
            result.add(current)
        return result

    @staticmethod
    def descendants(node_id: str, edges: list[GraphEdgeSpec]) -> set[str]:
        children: dict[str, list[str]] = defaultdict(list)
        for edge in edges:
            children[edge.source].append(edge.target)
        result = {node_id}
        queue = deque([node_id])
        while queue:
            current = queue.popleft()
            for child in children.get(current, []):
                if child not in result:
                    result.add(child)
                    queue.append(child)
        return result
