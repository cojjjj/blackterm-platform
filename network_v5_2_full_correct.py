from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from PySide6.QtCore import QPointF, QRectF, QTimer, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QFrame, QGraphicsEllipseItem, QGraphicsItem, QGraphicsObject,
    QGraphicsPathItem, QGraphicsScene, QGraphicsTextItem, QGraphicsView,
    QHBoxLayout, QLabel, QPushButton, QSlider, QTextEdit, QVBoxLayout, QWidget
)


from ..network_model import DEVICE_COLORS, DEVICE_GLYPHS, classify_host, exposure_color, exposure_score, explain_host


@dataclass(slots=True)
class HostProfile:
    key: str
    ip: str
    hostname: str
    open_ports: list[int] = field(default_factory=list)
    services: list[str] = field(default_factory=list)
    scan_id: int | None = None
    device_type: str = "unknown"
    device_label: str = "Unknown host"
    latency_ms: float = 0.0
    status: str = "OBSERVED"

    @property
    def open_count(self) -> int:
        return len(self.open_ports)


class EdgeItem(QGraphicsPathItem):
    def __init__(self, source: "HostNode", target: "HostNode"):
        super().__init__()
        self.source = source
        self.target = target
        self.setZValue(-5)
        self.setPen(QPen(QColor("#4b315c"), 2))
        self.packet_phase = 0.0
        self.packet = QGraphicsEllipseItem(-4, -4, 8, 8, self)
        self.packet.setBrush(QBrush(QColor("#c000ff")))
        self.packet.setPen(Qt.NoPen)
        self.update_path()

    def update_path(self):
        start = self.source.scenePos()
        end = self.target.scenePos()
        path = QPainterPath(start)
        dx = end.x() - start.x()
        control1 = QPointF(start.x() + dx * 0.35, start.y())
        control2 = QPointF(start.x() + dx * 0.65, end.y())
        path.cubicTo(control1, control2, end)
        self.setPath(path)
        self.update_packet()

    def update_packet(self):
        point = self.path().pointAtPercent(self.packet_phase)
        self.packet.setPos(point)

    def tick(self, delta=0.018):
        self.packet_phase = (self.packet_phase + delta) % 1.0
        self.update_packet()


class HostNode(QGraphicsObject):
    selected_profile = Signal(object)

    def __init__(self, profile: HostProfile, radius: float = 28.0):
        super().__init__()
        self.profile = profile
        self.radius = radius
        self.edges: list[EdgeItem] = []
        self.hovered = False
        self.heatmap_enabled = False
        self.pulse = 0.0
        self.setFlags(
            QGraphicsItem.ItemIsMovable
            | QGraphicsItem.ItemIsSelectable
            | QGraphicsItem.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)
        self.setToolTip(self.tooltip_text())
        self.setZValue(10)

        self.label = QGraphicsTextItem(self)
        self.label.setDefaultTextColor(QColor("#f5efff"))
        self.label.setFont(QFont("Segoe UI", 9))
        self.label.setPlainText(self.short_label())
        self.label.setTextWidth(150)
        self.label.setPos(-75, radius + 8)

    def boundingRect(self) -> QRectF:
        extra = 14 if self.hovered else 8
        return QRectF(
            -self.radius - extra,
            -self.radius - extra,
            (self.radius + extra) * 2,
            (self.radius + extra) * 2 + 52,
        )

    def short_label(self):
        host = self.profile.hostname
        if not host or host == "Unknown":
            host = self.profile.ip
        return f"{host}\n{self.profile.open_count} open"

    def tooltip_text(self):
        services = ", ".join(self.profile.services) or "None observed"
        ports = ", ".join(map(str, self.profile.open_ports)) or "None"
        return (
            f"{self.profile.hostname or self.profile.ip}\n"
            f"{self.profile.device_label}\n"
            f"IP: {self.profile.ip}\n"
            f"Open ports: {ports}\n"
            f"Services: {services}"
        )

    def refresh_profile(self, profile: HostProfile):
        self.profile = profile
        self.label.setPlainText(self.short_label())
        self.setToolTip(self.tooltip_text())
        self.update()

    def paint(self, painter: QPainter, option, widget=None):
        painter.setRenderHint(QPainter.Antialiasing)
        score, _ = exposure_score(self.profile.open_ports, self.profile.services)
        base = DEVICE_COLORS.get(self.profile.device_type, "#ff5c7a")
        color = QColor(exposure_color(score) if getattr(self, "heatmap_enabled", False) else base)

        pulse_radius = self.radius + 8 + self.pulse * 7
        glow = QColor(color)
        glow.setAlpha(38 + int(self.pulse * 25))
        painter.setPen(Qt.NoPen)
        painter.setBrush(glow)
        painter.drawEllipse(QPointF(0, 0), pulse_radius, pulse_radius)

        if self.isSelected() or self.hovered:
            selection = QColor("#ffffff")
            selection.setAlpha(175)
            painter.setPen(QPen(selection, 2))
        else:
            painter.setPen(QPen(QColor("#ffffff"), 1))

        painter.setBrush(color)
        painter.drawEllipse(QPointF(0, 0), self.radius, self.radius)

        painter.setPen(QColor("#08060d"))
        font = QFont("Segoe UI Symbol", 16, QFont.Bold)
        painter.setFont(font)
        glyph = DEVICE_GLYPHS.get(self.profile.device_type, "?")
        painter.drawText(
            QRectF(-self.radius, -self.radius, self.radius * 2, self.radius * 2),
            Qt.AlignCenter,
            glyph,
        )

    def hoverEnterEvent(self, event):
        self.hovered = True
        self.setScale(1.08)
        self.prepareGeometryChange()
        self.update()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.hovered = False
        self.heatmap_enabled = False
        self.setScale(1.0)
        self.prepareGeometryChange()
        self.update()
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event):
        self.selected_profile.emit(self.profile)
        super().mousePressEvent(event)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionHasChanged:
            for edge in self.edges:
                edge.update_path()
        return super().itemChange(change, value)


class NetworkView(QGraphicsView):
    profile_selected = Signal(object)

    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.scene_obj = QGraphicsScene(self)
        self.setScene(self.scene_obj)
        self.setRenderHints(
            QPainter.Antialiasing
            | QPainter.TextAntialiasing
            | QPainter.SmoothPixmapTransform
        )
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)
        self.setBackgroundBrush(QBrush(QColor("#07050b")))
        self.setFrameShape(QFrame.NoFrame)
        self.setSceneRect(-700, -470, 1400, 940)

        self.nodes: dict[str, HostNode] = {}
        self.edges: list[EdgeItem] = []
        self.core = self.create_core()
        self.phase = 0.0
        self.replay_events: list[dict[str, Any]] = []
        self.heatmap_enabled = False
        self.replay_index = 0

        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self.animate)
        self.animation_timer.start(35)

        self.replay_timer = QTimer(self)
        self.replay_timer.timeout.connect(self.replay_step)

    def create_core(self):
        profile = HostProfile(
            key="blackterm-core",
            ip="LOCAL",
            hostname="BLACKTERM CORE",
            device_type="core",
            device_label="BLACKTERM intelligence core",
            status="ACTIVE",
        )
        node = HostNode(profile, radius=34)
        node.setFlag(QGraphicsItem.ItemIsMovable, False)
        node.setPos(0, 0)
        node.selected_profile.connect(self.profile_selected)
        self.scene_obj.addItem(node)
        return node

    def wheelEvent(self, event):
        zoom_in = 1.16
        zoom_out = 1 / zoom_in
        factor = zoom_in if event.angleDelta().y() > 0 else zoom_out
        current = self.transform().m11()
        target = current * factor
        if 0.25 <= target <= 4.5:
            self.scale(factor, factor)

    def set_heatmap(self, enabled: bool):
        self.heatmap_enabled = enabled
        for node in self.nodes.values():
            node.heatmap_enabled = enabled
            node.update()

    def animate(self):
        self.phase = (self.phase + 0.045) % (2 * math.pi)
        pulse = (math.sin(self.phase) + 1) / 2
        for node in self.nodes.values():
            node.pulse = pulse
            node.update()
        self.core.pulse = pulse
        self.core.update()
        for edge in self.edges:
            edge.tick()

    def clear_hosts(self):
        for edge in self.edges:
            self.scene_obj.removeItem(edge)
        for node in list(self.nodes.values()):
            self.scene_obj.removeItem(node)
        self.edges.clear()
        self.nodes.clear()

    def add_or_update_host(self, profile: HostProfile, animate=True):
        existing = self.nodes.get(profile.key)
        if existing:
            existing.refresh_profile(profile)
            return existing

        node = HostNode(profile)
        node.selected_profile.connect(self.profile_selected)
        node.setOpacity(0.0 if animate else 1.0)
        self.scene_obj.addItem(node)
        self.nodes[profile.key] = node

        edge = EdgeItem(self.core, node)
        self.scene_obj.addItem(edge)
        self.edges.append(edge)
        self.core.edges.append(edge)
        node.edges.append(edge)

        index = len(self.nodes) - 1
        angle = (2 * math.pi * index / max(1, len(self.nodes))) - math.pi / 2
        ring = 270 + (index // 8) * 135
        node.setPos(math.cos(angle) * ring, math.sin(angle) * ring)

        if animate:
            node.setOpacity(1.0)
        edge.update_path()
        return node

    def load_history(self):
        self.clear_hosts()
        unique: dict[str, dict] = {}
        for row in self.engine.repository.list_recent(40):
            unique.setdefault(row["ip"], row)

        for row in unique.values():
            result = self.engine.repository.get(row["id"])
            if result is None:
                continue
            services = sorted({p.service for p in result.open_ports})
            device_type, label = classify_host(set(services))
            profile = HostProfile(
                key=result.ip,
                ip=result.ip,
                hostname=result.hostname or "Unknown",
                open_ports=[p.port for p in result.open_ports],
                services=services,
                scan_id=row["id"],
                device_type=device_type,
                device_label=label,
                latency_ms=result.average_open_latency,
            )
            self.add_or_update_host(profile, animate=False)
        self.auto_layout()

    def auto_layout(self):
        nodes = list(self.nodes.values())
        if not nodes:
            return
        layers: dict[str, list[HostNode]] = {
            "network": [],
            "web": [],
            "windows": [],
            "linux": [],
            "unknown": [],
        }
        for node in nodes:
            layers.setdefault(node.profile.device_type, []).append(node)

        y_positions = {
            "network": -300,
            "web": -145,
            "windows": 80,
            "linux": 235,
            "unknown": 350,
        }
        for device_type, group in layers.items():
            if not group:
                continue
            spacing = 210
            start_x = -(len(group) - 1) * spacing / 2
            for idx, node in enumerate(group):
                node.setPos(start_x + idx * spacing, y_positions.get(device_type, 320))
        self.core.setPos(0, -15)
        for edge in self.edges:
            edge.update_path()
        self.fit_all()

    def fit_all(self):
        bounds = self.scene_obj.itemsBoundingRect().adjusted(-90, -90, 90, 90)
        self.fitInView(bounds, Qt.KeepAspectRatio)

    def focus_profile(self, profile: HostProfile):
        node = self.nodes.get(profile.key)
        if not node:
            return
        self.centerOn(node)
        node.setSelected(True)

    def begin_live_scan(self, target: str):
        profile = HostProfile(
            key=f"live:{target}",
            ip=target,
            hostname="DISCOVERING...",
            status="SCANNING",
            device_type="unknown",
            device_label="Live scan target",
        )
        node = self.add_or_update_host(profile)
        node.setPos(0, 235)
        for edge in node.edges:
            edge.update_path()

    def live_port(self, target: str, item):
        key = f"live:{target}"
        node = self.nodes.get(key)
        if node is None:
            self.begin_live_scan(target)
            node = self.nodes[key]
        profile = node.profile
        ports = sorted(set(profile.open_ports + [item.port]))
        services = sorted(set(profile.services + [item.service]))
        device_type, label = classify_host(set(services))
        node.refresh_profile(
            HostProfile(
                key=key,
                ip=target,
                hostname=profile.hostname,
                open_ports=ports,
                services=services,
                device_type=device_type,
                device_label=label,
                latency_ms=item.latency_ms or profile.latency_ms,
                status="SCANNING",
            )
        )

    def finish_live_scan(self, scan_id: int, result):
        live_key = f"live:{result.target}"
        live_node = self.nodes.pop(live_key, None)
        services = sorted({p.service for p in result.open_ports})
        device_type, label = classify_host(set(services))
        profile = HostProfile(
            key=result.ip,
            ip=result.ip,
            hostname=result.hostname or "Unknown",
            open_ports=[p.port for p in result.open_ports],
            services=services,
            scan_id=scan_id,
            device_type=device_type,
            device_label=label,
            latency_ms=result.average_open_latency,
            status="COMPLETE",
        )
        if live_node:
            live_node.profile = profile
            live_node.refresh_profile(profile)
            self.nodes[result.ip] = live_node
        else:
            self.add_or_update_host(profile)
        self.auto_layout()
        self.profile_selected.emit(profile)

    def replay_latest(self):
        rows = self.engine.repository.list_recent(1)
        if not rows:
            return False
        scan_id = rows[0]["id"]
        result = self.engine.repository.get(scan_id)
        events = self.engine.repository.get_events(scan_id)
        if result is None:
            return False

        self.replay_events = events or [
            {"event_type": "START", "message": f"Scan started for {result.target}"},
            *[
                {"event_type": "OPEN", "message": f"{p.port}/tcp {p.service}"}
                for p in result.open_ports
            ],
            {"event_type": "DONE", "message": "Scan completed"},
        ]
        self.replay_result = result
        self.replay_scan_id = scan_id
        self.replay_index = 0

        key = f"replay:{result.ip}"
        existing = self.nodes.pop(result.ip, None)
        if existing:
            self.scene_obj.removeItem(existing)
        profile = HostProfile(
            key=key,
            ip=result.ip,
            hostname="REPLAYING...",
            device_type="unknown",
            device_label="Timeline replay target",
            status="REPLAY",
        )
        node = self.add_or_update_host(profile)
        node.setPos(0, 250)
        for edge in node.edges:
            edge.update_path()
        self.replay_timer.start(600)
        return True

    def replay_step(self):
        if self.replay_index >= len(self.replay_events):
            self.replay_timer.stop()
            self.finish_live_scan(self.replay_scan_id, self.replay_result)
            return
        event = self.replay_events[self.replay_index]
        kind = event.get("event_type", "")
        message = event.get("message", "")
        if kind == "OPEN":
            port = None
            service = "unknown"
            parts = message.split()
            if parts:
                try:
                    port = int(parts[0].split("/")[0])
                except ValueError:
                    port = None
            if len(parts) > 1:
                service = parts[1]
            if port is not None:
                item = type("ReplayItem", (), {
                    "port": port,
                    "service": service,
                    "latency_ms": 0.0,
                })()
                self.live_port(self.replay_result.target, item)
        self.replay_index += 1


class NetworkPage(QWidget):
    def __init__(self, engine):
        super().__init__()
        self.engine = engine
        layout = QVBoxLayout(self)

        title = QLabel("BLACKTERM Live Intelligence")
        title.setObjectName("pageTitle")
        subtitle = QLabel(
            "Drag nodes, zoom with the mouse wheel, inspect hosts, optimize layout, "
            "and replay the latest scan timeline."
        )
        subtitle.setObjectName("muted")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        controls = QHBoxLayout()
        optimize = QPushButton("OPTIMIZE LAYOUT")
        optimize.clicked.connect(lambda: self.view.auto_layout())
        fit = QPushButton("FIT MAP")
        fit.clicked.connect(lambda: self.view.fit_all())
        self.heatmap = QPushButton("EXPOSURE HEATMAP")
        self.heatmap.setCheckable(True)
        replay = QPushButton("REPLAY LATEST SCAN")
        replay.setObjectName("primary")
        replay.clicked.connect(self.replay_latest)
        controls.addWidget(optimize)
        controls.addWidget(fit)
        controls.addWidget(self.heatmap)
        controls.addStretch()
        controls.addWidget(replay)
        layout.addLayout(controls)

        body = QHBoxLayout()
        self.view = NetworkView(engine)
        self.view.profile_selected.connect(self.show_profile)
        self.heatmap.toggled.connect(self.view.set_heatmap)
        body.addWidget(self.view, 4)

        panel = QFrame()
        panel.setObjectName("panel")
        panel.setMinimumWidth(310)
        panel.setMaximumWidth(380)
        panel_layout = QVBoxLayout(panel)
        panel_layout.addWidget(QLabel("HOST PROFILE"))
        self.profile = QTextEdit()
        self.profile.setReadOnly(True)
        self.profile.setPlainText(
            "Select or hover over a network node.\n\n"
            "Blue: Windows-like\n"
            "Green: Unix/Linux-like\n"
            "Amber: Web services\n"
            "Orange: Network infrastructure\n"
            "Red: Unknown"
        )
        panel_layout.addWidget(self.profile, 1)
        explain = QPushButton("EXPLAIN THIS HOST")
        explain.setObjectName("primary")
        explain.clicked.connect(self.explain_selected)
        panel_layout.addWidget(explain)
        self.selected_profile = None
        self.timeline = QTextEdit()
        self.timeline.setReadOnly(True)
        self.timeline.setMaximumHeight(230)
        panel_layout.addWidget(QLabel("SCAN TIMELINE"))
        panel_layout.addWidget(self.timeline)
        body.addWidget(panel, 1)
        layout.addLayout(body, 1)
        self.refresh()

    def explain_selected(self):
        if self.selected_profile is None:
            self.profile.append("\n\nSelect a host first.")
            return
        self.profile.append("\n\n" + explain_host(self.selected_profile))

    def show_profile(self, profile: HostProfile):
        self.selected_profile = profile
        ports = ", ".join(map(str, profile.open_ports)) or "None"
        score, score_label = exposure_score(profile.open_ports, profile.services)
        services = "\n".join(f"• {service}" for service in profile.services) or "None"
        self.profile.setPlainText(
            f"{profile.hostname or profile.ip}\n\n"
            f"TYPE\n{profile.device_label}\n\n"
            f"IP\n{profile.ip}\n\n"
            f"STATUS\n{profile.status}\n\n"
            f"OPEN PORTS\n{ports}\n\n"
            f"SERVICES\n{services}\n\n"
            f"AVERAGE LATENCY\n{profile.latency_ms} ms\n\n"
            f"EXPOSURE INDEX\n{score}/100 — {score_label}"
        )
        self.timeline.clear()
        if profile.scan_id is not None:
            events = self.engine.repository.get_events(profile.scan_id)
            for event in events:
                self.timeline.append(
                    f"{event['event_time']}\n"
                    f"[{event['event_type']}] {event['message']}\n"
                )
            if not events:
                self.timeline.setPlainText("No saved timeline events for this scan.")

    def replay_latest(self):
        if not self.view.replay_latest():
            self.timeline.setPlainText("No saved scan is available to replay.")
        else:
            self.timeline.setPlainText("Timeline replay started...")

    def refresh(self):
        self.view.load_history()

    def scan_started(self, target: str):
        self.view.begin_live_scan(target)
        self.timeline.setPlainText(f"LIVE\nScan started for {target}")

    def scan_progress(self, target: str, item):
        if item.state == "open":
            self.view.live_port(target, item)
            self.timeline.append(
                f"[OPEN] {item.port}/tcp {item.service} {item.latency_ms} ms"
            )

    def scan_finished(self, scan_id: int, result):
        self.view.finish_live_scan(scan_id, result)
        self.timeline.append(
            f"[DONE] Scan #{scan_id} completed with {len(result.open_ports)} open port(s)."
        )
