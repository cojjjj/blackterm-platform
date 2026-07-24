from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QEasingCurve, QPointF, QRectF, Qt, QTimer, Signal, QPropertyAnimation
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen, QBrush
from shiboken6 import isValid

from PySide6.QtWidgets import (
    QGraphicsItem,
    QGraphicsObject,
    QGraphicsPathItem,
    QGraphicsEllipseItem,
    QGraphicsScene,
    QGraphicsView,
    QWidget,
)

from ..attack_surface import AttackSurface


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
    "service": "◆",
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
    port: int | None = None
    service: str | None = None
    technology: str | None = None
    severity: str | None = None
    finding_index: int | None = None


class SurfaceNode(QGraphicsObject):
    activated = Signal(object)

    def __init__(
        self,
        data: GraphNodeData,
        width: float,
        height: float,
        accent: str,
        parent: QGraphicsItem | None = None,
    ):
        super().__init__(parent)
        self.data = data
        self.width = width
        self.height = height
        self.accent = QColor(accent)
        self._hovered = False
        self.setAcceptHoverEvents(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setToolTip(f"{data.title}\n{data.subtitle}\nClick for details")
        self.setOpacity(0.0)
        self._fade_animation: QPropertyAnimation | None = None

    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, self.width, self.height)

    def paint(self, painter: QPainter, option, widget: QWidget | None = None) -> None:
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.boundingRect()

        glow = QColor(self.accent)
        glow.setAlpha(80 if self._hovered or self.isSelected() else 34)
        painter.setPen(QPen(glow, 6 if self._hovered else 3))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(rect.adjusted(2, 2, -2, -2), 12, 12)

        background = QColor("#09111f")
        if self._hovered or self.isSelected():
            background = QColor("#10243a")
        painter.setPen(QPen(self.accent, 1.5))
        painter.setBrush(QBrush(background))
        painter.drawRoundedRect(rect.adjusted(5, 5, -5, -5), 10, 10)

        icon_rect = QRectF(10, 10, 28, self.height - 20)
        icon_font = QFont("Segoe UI Symbol", 14)
        icon_font.setBold(True)
        painter.setFont(icon_font)
        painter.setPen(self.accent)
        painter.drawText(icon_rect, Qt.AlignCenter, NODE_ICONS.get(self.data.kind, "◆"))

        text_left = 42
        painter.setPen(self.accent)
        title_font = QFont("Segoe UI", 9)
        title_font.setBold(True)
        painter.setFont(title_font)
        painter.drawText(
            rect.adjusted(text_left, 8, -10, -25),
            Qt.AlignLeft | Qt.AlignVCenter | Qt.TextWordWrap,
            self.data.title,
        )

        painter.setPen(QColor("#a9bfd7"))
        subtitle_font = QFont("Segoe UI", 7)
        painter.setFont(subtitle_font)
        painter.drawText(
            rect.adjusted(text_left, self.height - 28, -10, -6),
            Qt.AlignLeft | Qt.AlignVCenter | Qt.TextWordWrap,
            self.data.subtitle,
        )

    def animate_in(self, delay_ms: int) -> None:
        """Fade the node in without touching Qt objects after scene teardown.

        A graph refresh clears the QGraphicsScene immediately, while delayed
        callbacks created by ``QTimer.singleShot`` may still be queued.  In
        that case the Python wrapper can remain alive after Qt has deleted
        the underlying C++ item.  Validate the wrapper and scene membership
        before constructing the animation, and keep a Python reference to the
        animation for its lifetime.
        """

        def start() -> None:
            try:
                if not isValid(self) or self.scene() is None:
                    return

                animation = QPropertyAnimation(self, b"opacity", self)
                animation.setDuration(260)
                animation.setStartValue(self.opacity())
                animation.setEndValue(1.0)
                animation.setEasingCurve(QEasingCurve.OutCubic)
                animation.finished.connect(self._clear_fade_animation)
                self._fade_animation = animation
                animation.start()
            except RuntimeError:
                # The scene may have been cleared between the validity check
                # and animation construction.  A refresh should never crash
                # the application, so safely ignore that stale callback.
                return

        QTimer.singleShot(max(0, delay_ms), start)

    def _clear_fade_animation(self) -> None:
        if isValid(self):
            self._fade_animation = None

    def hoverEnterEvent(self, event) -> None:
        self._hovered = True
        self.update()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event) -> None:
        self._hovered = False
        self.update()
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.activated.emit(self.data)
        super().mousePressEvent(event)


class AttackSurfaceGraph(QGraphicsView):
    nodeActivated = Signal(object)

    graphRendered = Signal(int, int)
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.setFrameShape(QGraphicsView.NoFrame)
        self.setBackgroundBrush(QColor("#050914"))
        self.setMinimumHeight(360)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)
        self.setStyleSheet("QGraphicsView{border:1px solid #244667;border-radius:10px;}")
        self._auto_fit = True
        self._edge_paths: list[QPainterPath] = []
        self._signal_dots: list[QGraphicsEllipseItem] = []
        self._signal_phase = 0.0
        self._signal_timer = QTimer(self)
        self._signal_timer.setInterval(32)
        self._signal_timer.timeout.connect(self._advance_signals)
        self._signal_timer.start()

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
            self.fitInView(self._scene.sceneRect(), Qt.KeepAspectRatio)

    def clear_surface(self, message: str = "Run an authorized scan to generate the graph.") -> None:
        self._scene.clear()
        self._edge_paths.clear()
        self._signal_dots.clear()
        item = self._scene.addText(message)
        item.setDefaultTextColor(QColor("#7890a8"))
        item.setFont(QFont("Segoe UI", 10))
        item.setPos(20, 20)
        self._scene.setSceneRect(0, 0, 900, 300)
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

    def _connect(self, scene: QGraphicsScene, start: QPointF, end: QPointF, color: QColor, width: float = 1.6) -> None:
        path = QPainterPath(start)
        midpoint = (start.y() + end.y()) / 2
        path.cubicTo(start.x(), midpoint, end.x(), midpoint, end.x(), end.y())
        edge = QGraphicsPathItem(path)
        edge.setPen(QPen(color, width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        edge.setOpacity(0.76)
        edge.setZValue(-1)
        scene.addItem(edge)
        self._edge_paths.append(path)
        if len(self._signal_dots) < 18:
            dot = QGraphicsEllipseItem(-3.5, -3.5, 7, 7)
            dot.setBrush(QBrush(color.lighter(145)))
            dot.setPen(QPen(color, 1.2))
            dot.setZValue(3)
            dot.setOpacity(0.9)
            scene.addItem(dot)
            self._signal_dots.append(dot)

    def _advance_signals(self) -> None:
        if not self._edge_paths or not self._signal_dots:
            return
        self._signal_phase = (self._signal_phase + 0.008) % 1.0
        for index, dot in enumerate(tuple(self._signal_dots)):
            try:
                if not isValid(dot) or dot.scene() is None:
                    continue
                path = self._edge_paths[index % len(self._edge_paths)]
                phase = (self._signal_phase + index * 0.13) % 1.0
                dot.setPos(path.pointAtPercent(phase))
                dot.setOpacity(0.35 + 0.65 * (1.0 - abs(phase - 0.5) * 2.0))
            except RuntimeError:
                continue

    def replay(self) -> None:
        self._signal_phase = 0.0
        self._auto_fit = True
        for index, item in enumerate(self._scene.items()):
            if isinstance(item, SurfaceNode):
                item.setOpacity(0.0)
                item.animate_in(index * 65)

    def fit_graph(self) -> None:
        self._auto_fit = True
        if not self._scene.sceneRect().isEmpty():
            self.fitInView(self._scene.sceneRect(), Qt.KeepAspectRatio)

    def _add_node(self, node: SurfaceNode, delay_ms: int) -> None:
        node.activated.connect(self.nodeActivated.emit)
        self._scene.addItem(node)
        node.animate_in(delay_ms)

    @staticmethod
    def _finding_matches_port(finding, port: int, service: str) -> bool:
        evidence = (getattr(finding, "evidence", "") or "").lower()
        title = (getattr(finding, "title", "") or "").lower()
        return f"{port}/tcp" in evidence or f"tcp/{port}" in evidence or (service and service.lower() in title)

    def render_surface(self, surface: AttackSurface | None) -> None:
        if surface is None:
            self.clear_surface()
            return

        self._scene.clear()
        self._edge_paths.clear()
        self._signal_dots.clear()
        self._signal_phase = 0.0
        self.resetTransform()
        self._auto_fit = True

        ports = list(surface.open_ports)
        technologies = list(surface.technologies)
        findings = list(surface.findings)

        node_width = 170.0
        node_height = 72.0
        side_margin = 70.0
        columns = min(6, max(1, len(ports)))
        total_width = max(1000.0, side_margin * 2 + columns * node_width + (columns - 1) * 36)
        center_x = total_width / 2

        internet = SurfaceNode(
            GraphNodeData("internet", "INTERNET / SCOPE", surface.profile.upper()),
            200,
            64,
            "#c135ff",
        )
        internet.setPos(center_x - 100, 20)
        self._add_node(internet, 0)

        target = SurfaceNode(
            GraphNodeData("target", surface.target, surface.hostname or surface.ip),
            250,
            80,
            "#31b7ff",
        )
        target.setPos(center_x - 125, 125)
        self._add_node(target, 120)
        self._connect(self._scene, QPointF(center_x, 84), QPointF(center_x, 125), QColor("#874cff"), 2.0)

        service_by_port: dict[int, str] = {}
        for port, service in zip(surface.open_ports, surface.services):
            service_by_port.setdefault(port, service)
        if len(surface.services) != len(surface.open_ports):
            service_by_port = {port: "service" for port in surface.open_ports}

        if not ports:
            empty = SurfaceNode(
                GraphNodeData("status", "NO OPEN PORTS", "Selected scan range"),
                210,
                66,
                "#36e6b0",
            )
            empty.setPos(center_x - 105, 290)
            self._add_node(empty, 240)
            self._connect(self._scene, QPointF(center_x, 205), QPointF(center_x, 290), QColor("#36e6b0"))
            self._scene.setSceneRect(0, 0, total_width, 440)
            self.fitInView(self._scene.sceneRect(), Qt.KeepAspectRatio)
            return

        gap_x = 36.0
        gap_y = 58.0
        rows = (len(ports) + columns - 1) // columns
        service_y = 300.0
        grid_width = columns * node_width + (columns - 1) * gap_x
        start_x = center_x - grid_width / 2

        service_nodes: dict[int, tuple[SurfaceNode, float, float, str]] = {}
        for index, port in enumerate(ports):
            row = index // columns
            column = index % columns
            x = start_x + column * (node_width + gap_x)
            y = service_y + row * (node_height + gap_y)
            service = service_by_port.get(port, "service")
            group = self._service_group(service)
            color = SERVICE_COLORS[group]
            node = SurfaceNode(
                GraphNodeData("service", f"TCP/{port}", service, port=port, service=service),
                node_width,
                node_height,
                color,
            )
            node.setPos(x, y)
            self._add_node(node, 240 + index * 75)
            self._connect(self._scene, QPointF(center_x, 205), QPointF(x + node_width / 2, y), QColor(color))
            service_nodes[port] = (node, x, y, service)

        branch_base_y = service_y + rows * (node_height + gap_y) + 20
        branch_items: list[tuple[float, float]] = []

        # Technology branches attach to web services when possible, otherwise to the target.
        web_ports = [port for port, (_, _, _, service) in service_nodes.items() if self._service_group(service) == "web"]
        tech_parent_ports = web_ports or ports[:1]
        for index, technology in enumerate(technologies[:12]):
            parent_port = tech_parent_ports[index % len(tech_parent_ports)] if tech_parent_ports else None
            if parent_port is not None:
                _, parent_x, parent_y, _ = service_nodes[parent_port]
                parent_center = QPointF(parent_x + node_width / 2, parent_y + node_height)
                x = parent_x + (index % 2) * 92 - 45
                y = branch_base_y + (index // max(1, len(tech_parent_ports))) * 78
            else:
                parent_center = QPointF(center_x, 205)
                x = center_x - 80
                y = branch_base_y
            tech = SurfaceNode(
                GraphNodeData("technology", technology, "Detected technology", technology=technology),
                160,
                58,
                "#7ed7ff",
            )
            tech.setPos(x, y)
            self._add_node(tech, 420 + index * 70)
            self._connect(self._scene, parent_center, QPointF(x + 80, y), QColor("#31b7ff"), 1.2)
            branch_items.append((x, y + 58))

        # Finding branches attach to the related service where possible.
        finding_y_base = branch_base_y + (110 if technologies else 0)
        for finding_index, finding in enumerate(findings[:14]):
            matched_port = next(
                (
                    port
                    for port, (_, _, _, service) in service_nodes.items()
                    if self._finding_matches_port(finding, port, service)
                ),
                None,
            )
            severity = (getattr(finding, "severity", "info") or "info").lower()
            accent = SEVERITY_COLORS.get(severity, "#31b7ff")
            if matched_port is not None:
                _, parent_x, parent_y, _ = service_nodes[matched_port]
                parent_center = QPointF(parent_x + node_width / 2, parent_y + node_height)
                x = parent_x - 5 + (finding_index % 2) * 96
                y = finding_y_base + (finding_index // 2) * 82
            else:
                parent_center = QPointF(center_x, 205)
                x = center_x - 90 + (finding_index % 3 - 1) * 205
                y = finding_y_base + (finding_index // 3) * 82
            title = getattr(finding, "title", "Finding")
            node = SurfaceNode(
                GraphNodeData(
                    "finding",
                    title,
                    severity.upper(),
                    port=matched_port,
                    severity=severity,
                    finding_index=finding_index,
                ),
                180,
                62,
                accent,
            )
            node.setPos(x, y)
            self._add_node(node, 520 + finding_index * 80)
            self._connect(self._scene, parent_center, QPointF(x + 90, y), QColor(accent), 1.4)
            branch_items.append((x, y + 62))

        max_service_bottom = service_y + rows * (node_height + gap_y)
        max_branch_bottom = max((bottom for _, bottom in branch_items), default=max_service_bottom)
        scene_height = max(520.0, max(max_service_bottom, max_branch_bottom) + 80)
        self._scene.setSceneRect(0, 0, total_width, scene_height)
        self.fitInView(self._scene.sceneRect(), Qt.KeepAspectRatio)
