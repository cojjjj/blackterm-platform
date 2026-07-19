from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt, Signal, QTimer
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QGraphicsItem,
    QGraphicsObject,
    QGraphicsPathItem,
    QGraphicsScene,
    QGraphicsTextItem,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..graph_model import GraphEdge, GraphNode, GraphSnapshot, build_graph_snapshot
from .animations import GraphicsItemAnimator


def _node_color(kind: str, risk: int) -> QColor:
    if risk >= 18:
        return QColor("#ff4d79")
    if risk >= 10:
        return QColor("#f0b85a")
    palette = {
        "CASE": "#a970ff",
        "SCAN": "#41c7ff",
        "TARGET": "#31e6b4",
        "DOMAIN": "#31e6b4",
        "IP": "#31e6b4",
        "SERVICE": "#f5d76e",
        "PORT": "#f5d76e",
        "DNS": "#58a6ff",
        "WHOIS": "#8b9cff",
        "SSL": "#74e0c2",
        "TLS": "#74e0c2",
        "HEADERS": "#78dce8",
        "SCREENSHOT": "#f38ba8",
        "FILE": "#cba6f7",
        "LOG": "#fab387",
        "OBSERVATION": "#bac2de",
        "AI": "#ff79c6",
        "FINDING": "#ff79c6",
    }
    return QColor(palette.get(kind.upper(), "#8995a8"))


class EdgeItem(QGraphicsPathItem):
    def __init__(self, edge: GraphEdge, source: "NodeItem", target: "NodeItem"):
        super().__init__()
        self.edge = edge
        self.source = source
        self.target = target
        self.setZValue(-10)
        confidence = max(25, min(100, edge.confidence))
        color = QColor("#53657d")
        color.setAlpha(80 + int(confidence * 1.2))
        self.setPen(QPen(color, 1.2 + confidence / 100.0))
        self.setToolTip(f"{edge.relationship} // confidence {edge.confidence}%")
        source.moved.connect(self.update_path)
        target.moved.connect(self.update_path)
        self.update_path()

    def update_path(self):
        start = self.source.scenePos()
        end = self.target.scenePos()
        delta = end - start
        curve = max(35.0, min(150.0, abs(delta.x()) * 0.24 + abs(delta.y()) * 0.12))
        path = QPainterPath(start)
        path.cubicTo(
            QPointF(start.x() + curve, start.y()),
            QPointF(end.x() - curve, end.y()),
            end,
        )
        self.setPath(path)


class NodeItem(QGraphicsObject):
    selected_node = Signal(object)
    moved = Signal()

    def __init__(self, node: GraphNode):
        super().__init__()
        self.node = node
        self.radius = 43.0 if node.kind == "CASE" else 34.0
        self.setPos(node.x, node.y)
        self.setFlags(
            QGraphicsItem.ItemIsMovable
            | QGraphicsItem.ItemIsSelectable
            | QGraphicsItem.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)
        self.setCacheMode(QGraphicsItem.DeviceCoordinateCache)
        self.setZValue(10)
        self._hovered = False
        self.label_item = QGraphicsTextItem(self)
        font = QFont("Consolas", 8)
        font.setBold(True)
        self.label_item.setFont(font)
        self.label_item.setDefaultTextColor(QColor("#eaf5ff"))
        short = node.label if len(node.label) <= 25 else node.label[:22] + "..."
        self.label_item.setPlainText(short)
        bounds = self.label_item.boundingRect()
        self.label_item.setPos(-bounds.width() / 2, self.radius + 7)
        self.setToolTip(
            f"{node.kind} // {node.label}\n{node.detail}\nRisk weight: {node.risk}"
        )

    def boundingRect(self) -> QRectF:
        pad = 13.0
        return QRectF(
            -self.radius - pad,
            -self.radius - pad,
            (self.radius + pad) * 2,
            (self.radius + pad) * 2 + 36,
        )

    def paint(self, painter: QPainter, option, widget=None):
        painter.setRenderHint(QPainter.Antialiasing)
        color = _node_color(self.node.kind, self.node.risk)
        glow = QColor(color)
        glow.setAlpha(65 if not self._hovered else 125)
        painter.setPen(QPen(glow, 8 if not self.isSelected() else 13))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(QPointF(0, 0), self.radius + 4, self.radius + 4)

        fill = QColor("#0c1827")
        if self._hovered:
            fill = QColor("#13263b")
        painter.setBrush(QBrush(fill))
        painter.setPen(QPen(color, 2.2 if not self.isSelected() else 3.5))
        painter.drawEllipse(QPointF(0, 0), self.radius, self.radius)

        painter.setPen(QColor("#f3f8ff"))
        kind_font = QFont("Consolas", 7)
        kind_font.setBold(True)
        painter.setFont(kind_font)
        painter.drawText(
            QRectF(-self.radius, -10, self.radius * 2, 20),
            Qt.AlignCenter,
            self.node.kind[:10],
        )

        if self.node.risk:
            badge_color = QColor("#ff4d79") if self.node.risk >= 18 else QColor("#f0b85a")
            painter.setBrush(badge_color)
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(QPointF(self.radius - 7, -self.radius + 7), 9, 9)
            painter.setPen(QColor("#07111d"))
            badge_font = QFont("Consolas", 6)
            badge_font.setBold(True)
            painter.setFont(badge_font)
            painter.drawText(
                QRectF(self.radius - 16, -self.radius - 2, 18, 18),
                Qt.AlignCenter,
                str(min(99, self.node.risk)),
            )

    def hoverEnterEvent(self, event):
        self._hovered = True
        self.setScale(1.08)
        self.update()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self._hovered = False
        self.setScale(1.0)
        self.update()
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event):
        self.selected_node.emit(self.node)
        super().mousePressEvent(event)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionHasChanged:
            self.moved.emit()
        return super().itemChange(change, value)


class GraphView(QGraphicsView):
    def __init__(self, scene: QGraphicsScene, parent=None):
        super().__init__(scene, parent)
        self.setRenderHints(
            QPainter.Antialiasing
            | QPainter.TextAntialiasing
            | QPainter.SmoothPixmapTransform
        )
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)
        self.setBackgroundBrush(QBrush(QColor("#07111d")))
        self.setFrameShape(QFrame.NoFrame)
        self.setMinimumHeight(420)

    def wheelEvent(self, event):
        factor = 1.18 if event.angleDelta().y() > 0 else 1 / 1.18
        current = self.transform().m11()
        target = current * factor
        if 0.18 <= target <= 4.5:
            self.scale(factor, factor)


class InvestigationGraph(QWidget):
    node_selected = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.snapshot = GraphSnapshot((), ())
        self.scene = QGraphicsScene(self)
        self.scene.setItemIndexMethod(QGraphicsScene.NoIndex)
        self.view = GraphView(self.scene, self)
        self.node_items: dict[str, NodeItem] = {}
        self.edge_items: list[EdgeItem] = []
        self._live_nodes: list[GraphNode] = []
        self._live_edges: list[GraphEdge] = []
        self._live_index = 0
        self._graphics_animator = GraphicsItemAnimator(self)
        self._live_timer = QTimer(self)
        self._live_timer.setInterval(180)
        self._live_timer.timeout.connect(self._reveal_next_live_node)

        root = QVBoxLayout(self)
        toolbar = QHBoxLayout()
        self.status = QLabel("GRAPH // WAITING FOR CORRELATION")
        self.status.setObjectName("sectionTitle")
        fit_button = QPushButton("FIT GRAPH")
        fit_button.clicked.connect(self.fit_graph)
        reset_button = QPushButton("RESET LAYOUT")
        reset_button.clicked.connect(self.reset_layout)
        export_button = QPushButton("EXPORT PNG")
        export_button.clicked.connect(self.export_png)
        toolbar.addWidget(self.status)
        toolbar.addStretch()
        toolbar.addWidget(fit_button)
        toolbar.addWidget(reset_button)
        toolbar.addWidget(export_button)
        root.addLayout(toolbar)
        root.addWidget(self.view, 1)

        self.detail = QLabel(
            "Select a node to inspect its intelligence context. "
            "Drag nodes to reorganize the workspace; use the mouse wheel to zoom."
        )
        self.detail.setWordWrap(True)
        self.detail.setMinimumHeight(58)
        self.detail.setObjectName("graphDetail")
        root.addWidget(self.detail)

    def clear_graph(self):
        self._live_timer.stop()
        self._graphics_animator.registry.stop_all()
        self.scene.clear()
        self.node_items.clear()
        self.edge_items.clear()
        self.snapshot = GraphSnapshot((), ())
        self.status.setText("GRAPH // WAITING FOR CORRELATION")
        self.detail.setText(
            "Run intelligence correlation to generate the investigation graph."
        )

    def set_report(self, report):
        self.snapshot = build_graph_snapshot(report.nodes, report.edges)
        self.render_snapshot(self.snapshot)
        self.status.setText(
            f"GRAPH // {len(self.snapshot.nodes)} NODES // "
            f"{len(self.snapshot.edges)} LINKS // {report.level} PRIORITY"
        )

    def set_report_live(self, report, *, interval_ms: int = 180):
        """Reveal graph nodes one by one while preserving the final stable layout."""
        self._live_timer.stop()
        self.snapshot = build_graph_snapshot(report.nodes, report.edges)
        self.scene.clear()
        self.node_items.clear()
        self.edge_items.clear()
        self._live_nodes = list(self.snapshot.nodes)
        self._live_edges = list(self.snapshot.edges)
        self._live_index = 0
        self._live_timer.setInterval(max(60, int(interval_ms)))
        self.status.setText(
            f"LIVE GRAPH // 0/{len(self._live_nodes)} NODES // {report.level} PRIORITY"
        )
        self.detail.setText(
            "BLACKTERM is constructing the investigation graph from live intelligence."
        )
        if self._live_nodes:
            self._live_timer.start()
        else:
            self.status.setText("LIVE GRAPH // NO CORRELATED NODES")

    def _reveal_next_live_node(self):
        if self._live_index >= len(self._live_nodes):
            self._live_timer.stop()
            self.status.setText(
                f"GRAPH // {len(self.snapshot.nodes)} NODES // "
                f"{len(self.snapshot.edges)} LINKS // LIVE BUILD COMPLETE"
            )
            self.fit_graph()
            return

        node = self._live_nodes[self._live_index]
        item = NodeItem(node)
        item.setOpacity(0.0)
        item.setScale(0.15)
        item.selected_node.connect(self._show_node)
        self.scene.addItem(item)
        self.node_items[node.node_id] = item

        self._graphics_animator.fade(
            item,
            start=0.0,
            end=1.0,
            duration=260,
        )
        self._graphics_animator.scale(
            item,
            start=0.15,
            end=1.0,
            duration=300,
        )

        for edge in self._live_edges:
            if edge.target != node.node_id and edge.source != node.node_id:
                continue
            source = self.node_items.get(edge.source)
            target = self.node_items.get(edge.target)
            if not source or not target:
                continue
            edge_item = EdgeItem(edge, source, target)
            edge_item.setOpacity(0.0)
            self.scene.addItem(edge_item)
            self.edge_items.append(edge_item)
            self._graphics_animator.fade(
                edge_item,
                start=0.0,
                end=1.0,
                duration=340,
            )

        self._live_index += 1
        self.status.setText(
            f"LIVE GRAPH // {self._live_index}/{len(self._live_nodes)} NODES // "
            f"{len(self.edge_items)} LINKS"
        )
        bounds = self.scene.itemsBoundingRect().adjusted(-100, -100, 100, 100)
        self.scene.setSceneRect(bounds)
        self.view.fitInView(bounds, Qt.KeepAspectRatio)

    def render_snapshot(self, snapshot: GraphSnapshot):
        self.scene.clear()
        self.node_items.clear()
        self.edge_items.clear()

        for node in snapshot.nodes:
            item = NodeItem(node)
            item.selected_node.connect(self._show_node)
            self.scene.addItem(item)
            self.node_items[node.node_id] = item

        for edge in snapshot.edges:
            source = self.node_items.get(edge.source)
            target = self.node_items.get(edge.target)
            if not source or not target:
                continue
            item = EdgeItem(edge, source, target)
            self.scene.addItem(item)
            self.edge_items.append(item)

        bounds = self.scene.itemsBoundingRect().adjusted(-120, -120, 120, 120)
        self.scene.setSceneRect(bounds)
        self.fit_graph()

    def _show_node(self, node: GraphNode):
        risk_label = "HIGH SIGNAL" if node.risk >= 18 else "WATCH" if node.risk >= 10 else "CONTEXT"
        detail = node.detail or "No additional detail recorded."
        self.detail.setText(
            f"{node.kind} // {node.label}    "
            f"RISK // {node.risk} ({risk_label})\n{detail}"
        )
        self.node_selected.emit(node)

    def fit_graph(self):
        if self.scene.items():
            self.view.fitInView(
                self.scene.itemsBoundingRect().adjusted(-90, -90, 90, 90),
                Qt.KeepAspectRatio,
            )

    def reset_layout(self):
        if not self.snapshot.nodes:
            return
        for node in self.snapshot.nodes:
            item = self.node_items.get(node.node_id)
            if item:
                item.setPos(node.x, node.y)
        self.fit_graph()

    def export_png(self):
        if not self.scene.items():
            QMessageBox.information(self, "Graph export", "There is no graph to export yet.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Investigation Graph",
            "blackterm_investigation_graph.png",
            "PNG Image (*.png)",
        )
        if not path:
            return
        output = Path(path)
        if output.suffix.lower() != ".png":
            output = output.with_suffix(".png")
        bounds = self.scene.itemsBoundingRect().adjusted(-80, -80, 80, 80)
        width = max(1200, int(bounds.width()))
        height = max(800, int(bounds.height()))
        pixmap = QPixmap(width, height)
        pixmap.fill(QColor("#07111d"))
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        self.scene.render(painter, QRectF(0, 0, width, height), bounds)
        painter.end()
        if not pixmap.save(str(output), "PNG"):
            QMessageBox.critical(self, "Graph export failed", "The PNG could not be written.")
            return
        QMessageBox.information(self, "Graph exported", str(output))
