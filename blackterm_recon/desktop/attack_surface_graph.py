from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QEasingCurve, QPointF, QRectF, Qt, QTimer, Signal, QPropertyAnimation
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen, QBrush
from PySide6.QtWidgets import (
    QGraphicsItem,
    QGraphicsObject,
    QGraphicsPathItem,
    QGraphicsScene,
    QGraphicsView,
    QWidget,
)

from ..attack_surface import AttackSurface
from .graph_engine import GraphEdgeSpec, GraphNodeSpec, HierarchicalGraphEngine


SERVICE_COLORS = {
    "web": "#31b7ff",
    "remote": "#c135ff",
    "database": "#ff8a4c",
    "network": "#36e6b0",
    "unknown": "#7890a8",
}
SEVERITY_COLORS = {
    "critical": "#ff5577",
    "high": "#ff8a4c",
    "medium": "#f5c451",
    "low": "#36e6b0",
    "info": "#31b7ff",
}
NODE_ICONS = {
    "internet": "◈",
    "target": "▣",
    "service": "◉",
    "technology": "✦",
    "finding": "!",
    "status": "✓",
}
WEB_SERVICES = {"http", "https", "http-proxy", "https-alt", "www", "ssl/http"}
REMOTE_SERVICES = {"ssh", "telnet", "vnc", "rdp", "ms-wbt-server", "microsoft-ds", "netbios-ssn"}
DATABASE_SERVICES = {"mysql", "postgresql", "mongodb", "redis", "ms-sql-s", "oracle"}


@dataclass(frozen=True, slots=True)
class GraphNodeData:
    kind: str
    title: str
    subtitle: str
    node_id: str = ""
    port: int | None = None
    service: str | None = None
    technology: str | None = None
    severity: str | None = None
    finding_index: int | None = None


class SurfaceNode(QGraphicsObject):
    activated = Signal(object)
    hovered = Signal(str, bool)
    collapseRequested = Signal(str)

    def __init__(self, data: GraphNodeData, width: float, height: float, accent: str):
        super().__init__()
        self.data = data
        self.width = width
        self.height = height
        self.accent = QColor(accent)
        self._hovered = False
        self._path_highlighted = False
        self._collapsed = False
        self.setAcceptHoverEvents(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setToolTip(f"{data.title}\n{data.subtitle}\nClick for details · Double-click to collapse")
        self.setOpacity(0.0)
        self.setScale(0.92)

    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, self.width, self.height)

    def set_path_highlighted(self, active: bool) -> None:
        if self._path_highlighted != active:
            self._path_highlighted = active
            self.update()

    def set_collapsed(self, collapsed: bool) -> None:
        self._collapsed = collapsed
        self.update()

    def paint(self, painter: QPainter, option, widget: QWidget | None = None) -> None:
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.boundingRect()
        active = self._hovered or self.isSelected() or self._path_highlighted

        glow = QColor(self.accent)
        glow.setAlpha(100 if active else 30)
        painter.setPen(QPen(glow, 7 if active else 3))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(rect.adjusted(2, 2, -2, -2), 14, 14)

        background = QColor("#10243a" if active else "#081321")
        painter.setPen(QPen(self.accent, 1.6 if active else 1.2))
        painter.setBrush(QBrush(background))
        painter.drawRoundedRect(rect.adjusted(6, 6, -6, -6), 11, 11)

        icon_font = QFont("Segoe UI Symbol", 15)
        icon_font.setBold(True)
        painter.setFont(icon_font)
        painter.setPen(self.accent)
        painter.drawText(QRectF(12, 10, 30, self.height - 20), Qt.AlignCenter, NODE_ICONS.get(self.data.kind, "◆"))

        title_font = QFont("Segoe UI", 9)
        title_font.setBold(True)
        painter.setFont(title_font)
        painter.drawText(
            rect.adjusted(48, 9, -14, -26),
            Qt.AlignLeft | Qt.AlignVCenter | Qt.TextWordWrap,
            self.data.title,
        )
        painter.setPen(QColor("#aac4dd"))
        subtitle_font = QFont("Segoe UI", 7)
        painter.setFont(subtitle_font)
        painter.drawText(
            rect.adjusted(48, self.height - 29, -14, -7),
            Qt.AlignLeft | Qt.AlignVCenter | Qt.TextWordWrap,
            self.data.subtitle,
        )

        if self._collapsed:
            painter.setPen(QPen(self.accent, 1.3))
            painter.setBrush(QColor("#07111f"))
            painter.drawEllipse(QRectF(self.width - 28, self.height - 28, 20, 20))
            painter.setFont(QFont("Segoe UI", 10, QFont.Bold))
            painter.drawText(QRectF(self.width - 28, self.height - 28, 20, 20), Qt.AlignCenter, "+")

    def animate_in(self, delay_ms: int) -> None:
        def start() -> None:
            opacity = QPropertyAnimation(self, b"opacity", self)
            opacity.setDuration(320)
            opacity.setStartValue(0.0)
            opacity.setEndValue(1.0)
            opacity.setEasingCurve(QEasingCurve.OutCubic)
            opacity.start(QPropertyAnimation.DeleteWhenStopped)

            scale = QPropertyAnimation(self, b"scale", self)
            scale.setDuration(360)
            scale.setStartValue(0.88)
            scale.setEndValue(1.0)
            scale.setEasingCurve(QEasingCurve.OutBack)
            scale.start(QPropertyAnimation.DeleteWhenStopped)

        QTimer.singleShot(delay_ms, start)

    def hoverEnterEvent(self, event) -> None:
        self._hovered = True
        self.hovered.emit(self.data.node_id, True)
        self.update()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event) -> None:
        self._hovered = False
        self.hovered.emit(self.data.node_id, False)
        self.update()
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.activated.emit(self.data)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.collapseRequested.emit(self.data.node_id)
            event.accept()
            return
        super().mouseDoubleClickEvent(event)


class SurfaceEdge(QGraphicsPathItem):
    def __init__(self, source_id: str, target_id: str, path: QPainterPath, accent: str, width: float):
        super().__init__(path)
        self.source_id = source_id
        self.target_id = target_id
        self.base_color = QColor(accent)
        self.base_width = width
        self.setZValue(-2)
        self.set_highlighted(False)

    def set_highlighted(self, active: bool) -> None:
        color = QColor(self.base_color)
        color.setAlpha(255 if active else 145)
        self.setPen(QPen(color, self.base_width + (1.8 if active else 0), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        self.setOpacity(1.0 if active else 0.72)


class AttackSurfaceGraph(QGraphicsView):
    nodeActivated = Signal(object)
    graphRendered = Signal(int, int)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.setFrameShape(QGraphicsView.NoFrame)
        self.setBackgroundBrush(QColor("#040914"))
        self.setMinimumHeight(520)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)
        self.setStyleSheet("QGraphicsView{border:1px solid #244667;border-radius:10px;}")
        self._layout_engine = HierarchicalGraphEngine()
        self._surface: AttackSurface | None = None
        self._node_specs: list[GraphNodeSpec] = []
        self._edge_specs: list[GraphEdgeSpec] = []
        self._nodes: dict[str, SurfaceNode] = {}
        self._edges: list[SurfaceEdge] = []
        self._collapsed: set[str] = set()
        self._auto_fit = True

    def wheelEvent(self, event) -> None:
        if event.modifiers() & Qt.ControlModifier:
            self._auto_fit = False
            factor = 1.15 if event.angleDelta().y() > 0 else 0.87
            self.scale(factor, factor)
            event.accept()
            return
        super().wheelEvent(event)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._auto_fit and not self._scene.sceneRect().isEmpty():
            QTimer.singleShot(0, self.fit_graph)

    def fit_graph(self) -> None:
        if self._scene.sceneRect().isEmpty():
            return
        self._auto_fit = True
        self.resetTransform()
        self.fitInView(self._scene.sceneRect(), Qt.KeepAspectRatio)
        # Keep small graphs comfortably readable.
        if self.transform().m11() > 1.12:
            self.resetTransform()
            self.scale(1.12, 1.12)
            self.centerOn(self._scene.sceneRect().center())

    def replay(self) -> None:
        for index, node in enumerate(sorted(self._nodes.values(), key=lambda item: item.pos().y())):
            node.setOpacity(0.0)
            node.setScale(0.9)
            node.animate_in(index * 85)

    def clear_surface(self, message: str = "Run an authorized scan to generate the graph.") -> None:
        self._scene.clear()
        self._nodes.clear()
        self._edges.clear()
        item = self._scene.addText(message)
        item.setDefaultTextColor(QColor("#7890a8"))
        item.setFont(QFont("Segoe UI", 10))
        item.setPos(24, 24)
        self._scene.setSceneRect(0, 0, 1050, 520)
        self._auto_fit = True

    @staticmethod
    def _service_group(service: str) -> str:
        value = service.lower()
        if value in WEB_SERVICES or "http" in value:
            return "web"
        if value in REMOTE_SERVICES:
            return "remote"
        if value in DATABASE_SERVICES:
            return "database"
        if value in {"unknown", "service"}:
            return "unknown"
        return "network"

    @staticmethod
    def _finding_matches_port(finding, port: int, service: str) -> bool:
        evidence = (getattr(finding, "evidence", "") or "").lower()
        title = (getattr(finding, "title", "") or "").lower()
        return f"{port}/tcp" in evidence or f"tcp/{port}" in evidence or (service and service.lower() in title)

    def _build_model(self, surface: AttackSurface) -> tuple[list[GraphNodeSpec], list[GraphEdgeSpec]]:
        nodes: list[GraphNodeSpec] = []
        edges: list[GraphEdgeSpec] = []

        scope_data = GraphNodeData("internet", "INTERNET / SCOPE", surface.profile.upper(), node_id="scope")
        target_data = GraphNodeData("target", surface.target, surface.hostname or surface.ip, node_id="target")
        nodes.extend([
            GraphNodeSpec("scope", "internet", scope_data.title, scope_data.subtitle, "#c135ff", scope_data, 210, 66),
            GraphNodeSpec("target", "target", target_data.title, target_data.subtitle, "#31b7ff", target_data, 255, 82),
        ])
        edges.append(GraphEdgeSpec("scope", "target", "#8c4dff", 2.2))

        services = list(surface.services)
        service_by_port = {
            port: (services[index] if index < len(services) else "service")
            for index, port in enumerate(surface.open_ports)
        }
        service_ids: dict[int, str] = {}
        for index, port in enumerate(surface.open_ports):
            service = service_by_port.get(port, "service")
            group = self._service_group(service)
            node_id = f"service:{port}:{index}"
            service_ids[port] = node_id
            data = GraphNodeData(
                "service", f"TCP/{port}", service, node_id=node_id, port=port, service=service
            )
            nodes.append(GraphNodeSpec(node_id, "service", data.title, data.subtitle, SERVICE_COLORS[group], data, 188, 70))
            edges.append(GraphEdgeSpec("target", node_id, SERVICE_COLORS[group], 1.7))

        if not surface.open_ports:
            data = GraphNodeData("status", "NO OPEN PORTS", "Selected scan range", node_id="status:empty")
            nodes.append(GraphNodeSpec("status:empty", "status", data.title, data.subtitle, "#36e6b0", data, 210, 66))
            edges.append(GraphEdgeSpec("target", "status:empty", "#36e6b0", 1.6))

        web_parents = [
            service_ids[port]
            for port, service in service_by_port.items()
            if port in service_ids and self._service_group(service) == "web"
        ]
        technology_parents = web_parents or list(service_ids.values())[:1] or ["target"]
        for index, technology in enumerate(surface.technologies[:18]):
            node_id = f"technology:{index}"
            data = GraphNodeData(
                "technology", technology, "Detected technology", node_id=node_id, technology=technology
            )
            nodes.append(GraphNodeSpec(node_id, "technology", data.title, data.subtitle, "#7ed7ff", data, 178, 62))
            parent = technology_parents[index % len(technology_parents)]
            edges.append(GraphEdgeSpec(parent, node_id, "#31b7ff", 1.35))

        for index, finding in enumerate(surface.findings[:20]):
            matched_port = next(
                (port for port, service in service_by_port.items() if self._finding_matches_port(finding, port, service)),
                None,
            )
            severity = (getattr(finding, "severity", "info") or "info").lower()
            node_id = f"finding:{index}"
            data = GraphNodeData(
                "finding",
                getattr(finding, "title", "Finding"),
                severity.upper(),
                node_id=node_id,
                port=matched_port,
                severity=severity,
                finding_index=index,
            )
            nodes.append(GraphNodeSpec(node_id, "finding", data.title, data.subtitle, SEVERITY_COLORS.get(severity, "#31b7ff"), data, 205, 66))
            parent = service_ids.get(matched_port, "target")
            edges.append(GraphEdgeSpec(parent, node_id, SEVERITY_COLORS.get(severity, "#31b7ff"), 1.55))

        return nodes, edges

    def render_surface(self, surface: AttackSurface | None) -> None:
        self._surface = surface
        if surface is None:
            self.clear_surface()
            return
        self._node_specs, self._edge_specs = self._build_model(surface)
        self._collapsed.intersection_update({node.node_id for node in self._node_specs})
        self._render_model(animate=True)

    def _render_model(self, animate: bool) -> None:
        self._scene.clear()
        self._nodes.clear()
        self._edges.clear()
        layout = self._layout_engine.layout(self._node_specs, self._edge_specs, "scope", self._collapsed)
        visible_ids = set(layout.positions)
        node_by_id = {node.node_id: node for node in self._node_specs}

        for edge_spec in self._edge_specs:
            if edge_spec.source not in visible_ids or edge_spec.target not in visible_ids:
                continue
            source_spec = node_by_id[edge_spec.source]
            target_spec = node_by_id[edge_spec.target]
            source_pos = layout.positions[edge_spec.source]
            target_pos = layout.positions[edge_spec.target]
            start = QPointF(source_pos.x() + source_spec.width / 2, source_pos.y() + source_spec.height)
            end = QPointF(target_pos.x() + target_spec.width / 2, target_pos.y())
            path = QPainterPath(start)
            control_y = start.y() + max(40.0, (end.y() - start.y()) * 0.52)
            path.cubicTo(start.x(), control_y, end.x(), control_y, end.x(), end.y())
            edge = SurfaceEdge(edge_spec.source, edge_spec.target, path, edge_spec.accent, edge_spec.width)
            self._scene.addItem(edge)
            self._edges.append(edge)

        ordered = sorted(visible_ids, key=lambda node_id: (layout.depth.get(node_id, 0), layout.positions[node_id].x()))
        for index, node_id in enumerate(ordered):
            spec = node_by_id[node_id]
            node = SurfaceNode(spec.payload, spec.width, spec.height, spec.accent)
            node.setPos(layout.positions[node_id])
            node.set_collapsed(node_id in self._collapsed)
            node.activated.connect(self.nodeActivated.emit)
            node.hovered.connect(self._highlight_path)
            node.collapseRequested.connect(self._toggle_collapsed)
            self._scene.addItem(node)
            self._nodes[node_id] = node
            if animate:
                node.animate_in(index * 90)
            else:
                node.setOpacity(1.0)
                node.setScale(1.0)

        self._scene.setSceneRect(layout.bounds)
        QTimer.singleShot(0, self.fit_graph)
        self.graphRendered.emit(len(self._nodes), len(self._edges))

    def _toggle_collapsed(self, node_id: str) -> None:
        has_children = any(edge.source == node_id for edge in self._edge_specs)
        if not has_children:
            return
        if node_id in self._collapsed:
            self._collapsed.remove(node_id)
        else:
            self._collapsed.add(node_id)
        self._render_model(animate=False)

    def _highlight_path(self, node_id: str, active: bool) -> None:
        if not active:
            for node in self._nodes.values():
                node.set_path_highlighted(False)
            for edge in self._edges:
                edge.set_highlighted(False)
            return
        related = self._layout_engine.ancestry(node_id, self._edge_specs)
        related.update(self._layout_engine.descendants(node_id, self._edge_specs))
        for current_id, node in self._nodes.items():
            node.set_path_highlighted(current_id in related)
        for edge in self._edges:
            edge.set_highlighted(edge.source_id in related and edge.target_id in related)
