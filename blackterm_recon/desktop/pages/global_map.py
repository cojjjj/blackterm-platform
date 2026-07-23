from __future__ import annotations

import json
import math
from dataclasses import dataclass
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from PySide6.QtCore import QPointF, Qt, QTimer, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QGraphicsEllipseItem,
    QGraphicsLineItem,
    QGraphicsPathItem,
    QGraphicsScene,
    QGraphicsTextItem,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


@dataclass(slots=True)
class IntelLocation:
    case_id: int
    case_name: str
    target: str
    latitude: float
    longitude: float
    city: str = ""
    region: str = ""
    country: str = ""
    organization: str = ""
    asn: str = ""
    ip: str = ""
    risk: int = 0
    confidence: int = 0
    created_at: str = ""

    @property
    def location_text(self) -> str:
        return ", ".join(value for value in (self.city, self.region, self.country) if value) or "Approximate location"

    @property
    def timestamp(self) -> datetime:
        raw = (self.created_at or "").replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(raw)
        except ValueError:
            return datetime.min


class MapMarker(QGraphicsEllipseItem):
    def __init__(self, record: IntelLocation, x: float, y: float):
        super().__init__(-6, -6, 12, 12)
        self.record = record
        self.base_x = x
        self.base_y = y
        self.setPos(x, y)
        self.setZValue(30)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(
            f"Case #{record.case_id} — {record.target}\n"
            f"{record.location_text}\n{record.organization or 'Organization unknown'}"
        )
        self.color = QColor("#36e6b0" if record.risk < 25 else "#ffd166" if record.risk < 50 else "#ff526f")
        self.setBrush(QBrush(self.color))
        self.setPen(QPen(QColor("#ffffff"), 1.4))


class GlobalMapView(QGraphicsView):
    location_selected = Signal(object)

    COUNTRY_ALIASES = {
        "united states": "United States of America",
        "usa": "United States of America",
        "russia": "Russia",
        "south korea": "South Korea",
        "north korea": "North Korea",
        "czech republic": "Czechia",
        "democratic republic of the congo": "Dem. Rep. Congo",
        "republic of the congo": "Congo",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene_obj = QGraphicsScene(self)
        self.setScene(self.scene_obj)
        self.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing | QPainter.SmoothPixmapTransform)
        self.setBackgroundBrush(QBrush(QColor("#050912")))
        self.setFrameShape(QFrame.NoFrame)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setSceneRect(-540, -300, 1080, 600)
        self.markers: list[MapMarker] = []
        self.pulse_items: list[QGraphicsEllipseItem] = []
        self.heat_items: list[QGraphicsEllipseItem] = []
        self.relation_items: list[QGraphicsPathItem] = []
        self.label_items: list[QGraphicsTextItem] = []
        self.country_items: dict[str, list[QGraphicsPathItem]] = {}
        self.show_heat = True
        self.show_relationships = True
        self.show_labels = True
        self._pulse_phase = 0
        self._dash_offset = 0.0
        self.animation_timer = QTimer(self)
        self.animation_timer.setInterval(55)
        self.animation_timer.timeout.connect(self._animate)
        self.animation_timer.start()
        self._draw_world()

    def wheelEvent(self, event):
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self.scale(factor, factor)

    def mousePressEvent(self, event):
        item = self.itemAt(event.position().toPoint())
        while item is not None:
            if isinstance(item, MapMarker):
                self.location_selected.emit(item.record)
                break
            item = item.parentItem()
        super().mousePressEvent(event)

    def reset_view(self):
        self.resetTransform()
        self.fitInView(self.sceneRect(), Qt.KeepAspectRatio)

    @staticmethod
    def _project_lonlat(lon: float, lat: float) -> QPointF:
        return QPointF(lon / 180.0 * 500.0, -lat / 90.0 * 250.0)

    def _geometry_path(self, geometry: dict[str, Any]) -> QPainterPath:
        path = QPainterPath()
        geom_type = geometry.get("type")
        coordinates = geometry.get("coordinates") or []
        polygons = [coordinates] if geom_type == "Polygon" else coordinates if geom_type == "MultiPolygon" else []
        for polygon in polygons:
            for ring in polygon:
                if not ring:
                    continue
                first = self._project_lonlat(float(ring[0][0]), float(ring[0][1]))
                path.moveTo(first)
                for lon, lat in ring[1:]:
                    path.lineTo(self._project_lonlat(float(lon), float(lat)))
                path.closeSubpath()
        return path

    def _draw_world(self):
        asset = Path(__file__).resolve().parents[2] / "assets" / "world_countries.geojson"
        try:
            payload = json.loads(asset.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            payload = {"features": []}

        for feature in payload.get("features") or []:
            name = str((feature.get("properties") or {}).get("name") or "Unknown")
            path = self._geometry_path(feature.get("geometry") or {})
            if path.isEmpty():
                continue
            item = QGraphicsPathItem(path)
            item.setBrush(QBrush(QColor("#0d2435")))
            item.setPen(QPen(QColor("#2870a1"), 0.75))
            item.setZValue(-5)
            item.setToolTip(name)
            self.scene_obj.addItem(item)
            self.country_items.setdefault(name, []).append(item)

        for lon in range(-150, 151, 30):
            x = lon / 180 * 500
            self.scene_obj.addLine(x, -250, x, 250, QPen(QColor(25, 70, 100, 55), 0.8, Qt.DotLine))
        for lat in range(-60, 61, 30):
            y = -lat / 90 * 250
            self.scene_obj.addLine(-500, y, 500, y, QPen(QColor(25, 70, 100, 55), 0.8, Qt.DotLine))

        label = QGraphicsTextItem("BLACKTERM GLOBAL INTELLIGENCE GRID // NATURAL EARTH")
        label.setDefaultTextColor(QColor("#31b7ff"))
        label.setFont(QFont("Segoe UI", 10, QFont.Bold))
        label.setPos(-515, -292)
        self.scene_obj.addItem(label)

    @staticmethod
    def project(record: IntelLocation) -> tuple[float, float]:
        x = max(-500.0, min(500.0, record.longitude / 180.0 * 500.0))
        y = max(-250.0, min(250.0, -record.latitude / 90.0 * 250.0))
        return x, y

    def set_layers(self, *, heat: bool, relationships: bool, labels: bool):
        self.show_heat = heat
        self.show_relationships = relationships
        self.show_labels = labels
        for item in self.heat_items:
            item.setVisible(heat)
        for item in self.relation_items:
            item.setVisible(relationships)
        for item in self.label_items:
            item.setVisible(labels)
        self._apply_country_heat()

    def _country_key(self, raw: str) -> str:
        cleaned = raw.strip().lower()
        return self.COUNTRY_ALIASES.get(cleaned, raw.strip())

    def _apply_country_heat(self):
        for items in self.country_items.values():
            for item in items:
                item.setBrush(QBrush(QColor("#0d2435")))
        if not self.show_heat:
            return
        scores: dict[str, list[int]] = {}
        for marker in self.markers:
            name = self._country_key(marker.record.country)
            if name:
                scores.setdefault(name, []).append(marker.record.risk)
        for name, risks in scores.items():
            intensity = min(100, max(12, len(risks) * 14 + int(sum(risks) / max(1, len(risks))) // 2))
            color = QColor("#36e6b0" if intensity < 35 else "#ffd166" if intensity < 65 else "#ff526f")
            color.setAlpha(55 + min(120, intensity))
            for item in self.country_items.get(name, []):
                item.setBrush(QBrush(color))

    def _relation_path(self, x1: float, y1: float, x2: float, y2: float) -> QPainterPath:
        path = QPainterPath(QPointF(x1, y1))
        midpoint = QPointF((x1 + x2) / 2.0, min(y1, y2) - 35 - abs(x2 - x1) * 0.06)
        path.quadTo(midpoint, QPointF(x2, y2))
        return path

    def set_locations(self, records: list[IntelLocation]):
        for group in (self.markers, self.pulse_items, self.heat_items, self.relation_items, self.label_items):
            for item in group:
                self.scene_obj.removeItem(item)
            group.clear()

        occupied: dict[tuple[int, int], int] = {}
        positions: list[tuple[IntelLocation, float, float]] = []
        for record in records:
            x, y = self.project(record)
            key = (round(x / 18), round(y / 18))
            offset = occupied.get(key, 0)
            occupied[key] = offset + 1
            x += (offset % 4) * 9
            y += (offset // 4) * 9
            positions.append((record, x, y))

            radius = 20 + min(30, record.risk * 0.30)
            heat = QGraphicsEllipseItem(-radius, -radius, radius * 2, radius * 2)
            heat.setPos(x, y)
            heat.setZValue(4)
            heat_color = QColor("#36e6b0" if record.risk < 25 else "#ffd166" if record.risk < 50 else "#ff526f")
            heat_color.setAlpha(24 + min(60, record.risk))
            heat.setBrush(QBrush(heat_color))
            heat.setPen(QPen(Qt.NoPen))
            heat.setVisible(self.show_heat)
            self.scene_obj.addItem(heat)
            self.heat_items.append(heat)

            pulse = QGraphicsEllipseItem(-10, -10, 20, 20)
            pulse.setPos(x, y)
            pulse.setZValue(20)
            pulse.setBrush(QBrush(Qt.NoBrush))
            pulse.setPen(QPen(QColor(54, 230, 176, 150), 1.4))
            self.scene_obj.addItem(pulse)
            self.pulse_items.append(pulse)

            marker = MapMarker(record, x, y)
            self.scene_obj.addItem(marker)
            self.markers.append(marker)

            text = QGraphicsTextItem(record.country or record.organization or record.target)
            text.setDefaultTextColor(QColor("#9edcff"))
            text.setFont(QFont("Segoe UI", 8, QFont.Bold))
            text.setPos(x + 10, y - 16)
            text.setZValue(32)
            text.setVisible(self.show_labels)
            self.scene_obj.addItem(text)
            self.label_items.append(text)

        for idx, (left, x1, y1) in enumerate(positions):
            for right, x2, y2 in positions[idx + 1:]:
                related = bool(
                    (left.organization and left.organization == right.organization)
                    or (left.asn and left.asn == right.asn)
                    or (left.target and left.target == right.target)
                )
                if not related:
                    continue
                line = QGraphicsPathItem(self._relation_path(x1, y1, x2, y2))
                pen = QPen(QColor(181, 45, 255, 155), 1.35, Qt.DashLine)
                pen.setDashPattern([5, 4])
                line.setPen(pen)
                line.setZValue(8)
                line.setVisible(self.show_relationships)
                self.scene_obj.addItem(line)
                self.relation_items.append(line)
        self._apply_country_heat()

    def _animate(self):
        self._pulse_phase = (self._pulse_phase + 1) % 48
        phase = self._pulse_phase / 48.0
        size = 18 + phase * 22
        alpha = int(185 * (1.0 - phase))
        for index, pulse in enumerate(self.pulse_items):
            shifted = ((self._pulse_phase + index * 7) % 48) / 48.0
            ring = 18 + shifted * 24
            pulse.setRect(-ring / 2, -ring / 2, ring, ring)
            color = QColor("#36e6b0")
            color.setAlpha(int(180 * (1.0 - shifted)))
            pulse.setPen(QPen(color, 1.25))
        self._dash_offset -= 0.55
        for relation in self.relation_items:
            pen = relation.pen()
            pen.setDashOffset(self._dash_offset)
            relation.setPen(pen)


class GlobalIntelligenceMapPage(QWidget):
    case_requested = Signal(int)

    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.records: list[IntelLocation] = []
        self.visible_records: list[IntelLocation] = []
        self.selected_case_id: int | None = None
        self.replay_timer = QTimer(self)
        self.replay_timer.setInterval(550)
        self.replay_timer.timeout.connect(self._advance_replay)

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(9)

        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("GLOBAL INTELLIGENCE MAP")
        title.setStyleSheet("font-size: 25px; font-weight: 900; color: #ffffff;")
        subtitle = QLabel("Geospatial case intelligence, infrastructure ownership, heat, and investigation relationships.")
        subtitle.setStyleSheet("color: #9db3ca;")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header.addLayout(title_box, 1)
        self.filter = QComboBox()
        self.filter.addItems(["ALL CASES", "ACTIVE / REVIEW", "HIGHER RISK"])
        self.filter.currentIndexChanged.connect(self.refresh)
        refresh = QPushButton("REFRESH INTELLIGENCE")
        refresh.clicked.connect(self.refresh)
        header.addWidget(self.filter)
        header.addWidget(refresh)
        root.addLayout(header)

        metrics = QHBoxLayout()
        self.case_metric = self._metric("MAPPED CASES")
        self.country_metric = self._metric("COUNTRIES")
        self.org_metric = self._metric("ORGANIZATIONS")
        self.target_metric = self._metric("TARGETS")
        for card in (self.case_metric, self.country_metric, self.org_metric, self.target_metric):
            metrics.addWidget(card)
        root.addLayout(metrics)

        controls = QHBoxLayout()
        controls.addWidget(QLabel("LAYERS"))
        self.heat_layer = QCheckBox("HEAT")
        self.relationship_layer = QCheckBox("RELATIONSHIPS")
        self.label_layer = QCheckBox("LABELS")
        for box in (self.heat_layer, self.relationship_layer, self.label_layer):
            box.setChecked(True)
            box.toggled.connect(self._apply_layers)
            controls.addWidget(box)
        controls.addSpacing(18)
        controls.addWidget(QLabel("TIMELINE"))
        self.timeline = QSlider(Qt.Horizontal)
        self.timeline.setRange(0, 0)
        self.timeline.valueChanged.connect(self._apply_timeline)
        controls.addWidget(self.timeline, 1)
        self.timeline_label = QLabel("ALL INTELLIGENCE")
        self.timeline_label.setMinimumWidth(140)
        controls.addWidget(self.timeline_label)
        self.replay = QPushButton("REPLAY")
        self.replay.clicked.connect(self._toggle_replay)
        fit = QPushButton("FIT")
        fit.clicked.connect(self.map_reset)
        controls.addWidget(self.replay)
        controls.addWidget(fit)
        root.addLayout(controls)

        split = QSplitter(Qt.Horizontal)
        self.map = GlobalMapView()
        self.map.location_selected.connect(self.show_location)
        split.addWidget(self.map)

        side = QFrame()
        side.setObjectName("intelMapSide")
        side.setStyleSheet("QFrame#intelMapSide { background:#080d17; border:1px solid #173a5a; border-radius:10px; }")
        side_layout = QVBoxLayout(side)
        self.details = QTextEdit()
        self.details.setReadOnly(True)
        self.details.setPlainText("Select a marker to inspect linked case intelligence.")
        self.open_case = QPushButton("OPEN LINKED CASE")
        self.open_case.setEnabled(False)
        self.open_case.clicked.connect(self._open_selected_case)
        side_layout.addWidget(QLabel("INTELLIGENCE DOSSIER"))
        side_layout.addWidget(self.details, 1)
        side_layout.addWidget(self.open_case)
        split.addWidget(side)
        split.setSizes([1000, 330])
        root.addWidget(split, 1)
        self.refresh()

    def map_reset(self):
        self.map.reset_view()

    def _metric(self, title: str) -> QFrame:
        card = QFrame()
        card.setProperty("metricTitle", title)
        card.setStyleSheet("QFrame { background:#0b0913; border:1px solid #264f72; border-radius:10px; }")
        layout = QVBoxLayout(card)
        label = QLabel(title)
        label.setStyleSheet("color:#8fa8c1; font-size:11px;")
        value = QLabel("0")
        value.setObjectName("value")
        value.setStyleSheet("color:#31b7ff; font-size:26px; font-weight:900;")
        layout.addWidget(label)
        layout.addWidget(value)
        card.value_label = value
        return card

    @staticmethod
    def _geo_from_raw(raw: dict[str, Any]) -> tuple[float, float, dict[str, Any]] | None:
        lat = raw.get("latitude")
        lon = raw.get("longitude")
        if isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
            return float(lat), float(lon), raw
        return None

    @classmethod
    def _extract_geo(cls, payload: dict[str, Any]) -> tuple[float, float, dict[str, Any]] | None:
        # Autonomous OSINT package.
        modules = payload.get("modules") or []
        for module in modules:
            if module.get("module") != "geoip" or module.get("status") != "success":
                continue
            for evidence in module.get("evidence") or []:
                try:
                    raw = json.loads(evidence.get("content") or "{}")
                except (TypeError, json.JSONDecodeError):
                    continue
                result = cls._geo_from_raw(raw)
                if result:
                    return result
        # Standalone GEOIP evidence saved by the intelligence persistence layer.
        return cls._geo_from_raw(payload)

    @staticmethod
    def _extract_asn(payload: dict[str, Any]) -> str:
        for module in payload.get("modules") or []:
            if module.get("module") != "asn" or module.get("status") != "success":
                continue
            for evidence in module.get("evidence") or []:
                try:
                    raw = json.loads(evidence.get("content") or "{}")
                except (TypeError, json.JSONDecodeError):
                    continue
                return str(raw.get("asn") or raw.get("AS") or "")
        return ""

    def _load_records(self) -> list[IntelLocation]:
        result: list[IntelLocation] = []
        cases = self.engine.repository.list_cases()
        for case in cases:
            if self.filter.currentIndex() == 1 and case.get("status") not in {"ACTIVE", "REVIEW"}:
                continue
            evidence_rows = self.engine.repository.case_evidence(int(case["id"]))
            osint_payload: dict[str, Any] | None = None
            standalone_geo: dict[str, Any] | None = None
            standalone_created = ""
            for evidence in evidence_rows:
                kind = str(evidence.get("evidence_type") or "").upper()
                try:
                    payload = json.loads(evidence.get("content") or "{}")
                except (TypeError, json.JSONDecodeError):
                    continue
                if kind == "OSINT":
                    osint_payload = payload
                    standalone_created = str(evidence.get("created_at") or "")
                    break
                if kind == "GEOIP" and self._extract_geo(payload):
                    standalone_geo = payload
                    standalone_created = str(evidence.get("created_at") or "")

            payload = osint_payload or standalone_geo
            if not payload:
                continue
            geo = self._extract_geo(payload)
            if not geo:
                continue
            lat, lon, raw = geo
            connection = raw.get("connection") or {}
            risk = int(payload.get("risk_score") or payload.get("risk") or 0)
            if self.filter.currentIndex() == 2 and risk < 25:
                continue
            target = str(payload.get("normalized_target") or payload.get("target") or raw.get("ip") or "unknown")
            result.append(IntelLocation(
                case_id=int(case["id"]),
                case_name=str(case.get("name") or ""),
                target=target,
                latitude=lat,
                longitude=lon,
                city=str(raw.get("city") or ""),
                region=str(raw.get("region") or ""),
                country=str(raw.get("country") or ""),
                organization=str(connection.get("org") or connection.get("isp") or ""),
                asn=self._extract_asn(payload),
                ip=str(raw.get("ip") or ""),
                risk=risk,
                confidence=int(payload.get("confidence") or 75),
                created_at=str(case.get("created_at") or standalone_created or ""),
            ))
        return sorted(result, key=lambda row: row.timestamp)

    def refresh(self):
        self.replay_timer.stop()
        self.replay.setText("REPLAY")
        self.records = self._load_records()
        max_index = max(0, len(self.records) - 1)
        self.timeline.blockSignals(True)
        self.timeline.setRange(0, max_index)
        self.timeline.setValue(max_index)
        self.timeline.blockSignals(False)
        self._apply_timeline()
        self.case_metric.value_label.setText(str(len({r.case_id for r in self.records})))
        self.country_metric.value_label.setText(str(len({r.country for r in self.records if r.country})))
        self.org_metric.value_label.setText(str(len({r.organization for r in self.records if r.organization})))
        self.target_metric.value_label.setText(str(len({r.target for r in self.records})))
        if not self.records:
            self.details.setPlainText(
                "No geolocated OSINT evidence is stored yet.\n\n"
                "Run an autonomous investigation or save an OSINT collection to a case, then refresh this map."
            )
        elif self.selected_case_id is None:
            self.details.setPlainText(self._intelligence_summary())


    def _intelligence_summary(self) -> str:
        countries = Counter(row.country for row in self.records if row.country)
        organizations = Counter(row.organization for row in self.records if row.organization)
        asns = Counter(row.asn for row in self.records if row.asn)
        top_country = countries.most_common(1)[0] if countries else ("Unknown", 0)
        top_org = organizations.most_common(1)[0] if organizations else ("Unknown", 0)
        top_asn = asns.most_common(1)[0] if asns else ("Unknown", 0)
        latest = self.records[-1]
        average_risk = round(sum(row.risk for row in self.records) / max(1, len(self.records)))
        return (
            "BLACKTERM GLOBAL INTELLIGENCE SUMMARY\n\n"
            f"MAPPED CASES: {len({row.case_id for row in self.records})}\n"
            f"COUNTRIES: {len(countries)}\n"
            f"AVERAGE RISK: {average_risk}/100\n\n"
            f"TOP COUNTRY: {top_country[0]} ({top_country[1]} record(s))\n"
            f"TOP ORGANIZATION: {top_org[0]} ({top_org[1]} record(s))\n"
            f"TOP ASN: {top_asn[0]} ({top_asn[1]} record(s))\n\n"
            f"LATEST TARGET: {latest.target}\n"
            f"LATEST LOCATION: {latest.location_text}\n"
            f"LATEST CASE: #{latest.case_id} — {latest.case_name}\n\n"
            "Select a pulsing marker to inspect its linked intelligence dossier."
        )

    def _apply_timeline(self):
        if not self.records:
            self.visible_records = []
            self.map.set_locations([])
            self.timeline_label.setText("NO INTELLIGENCE")
            return
        cutoff = min(self.timeline.value(), len(self.records) - 1)
        self.visible_records = self.records[: cutoff + 1]
        self.map.set_locations(self.visible_records)
        self._apply_layers()
        stamp = self.visible_records[-1].timestamp
        self.timeline_label.setText(stamp.strftime("%Y-%m-%d %H:%M") if stamp != datetime.min else f"{len(self.visible_records)} RECORD(S)")

    def _apply_layers(self):
        self.map.set_layers(
            heat=self.heat_layer.isChecked(),
            relationships=self.relationship_layer.isChecked(),
            labels=self.label_layer.isChecked(),
        )

    def _toggle_replay(self):
        if not self.records:
            return
        if self.replay_timer.isActive():
            self.replay_timer.stop()
            self.replay.setText("REPLAY")
            return
        self.timeline.setValue(0)
        self.replay.setText("PAUSE")
        self.replay_timer.start()

    def _advance_replay(self):
        if self.timeline.value() >= self.timeline.maximum():
            self.replay_timer.stop()
            self.replay.setText("REPLAY")
            return
        self.timeline.setValue(self.timeline.value() + 1)

    def show_location(self, record: IntelLocation):
        self.selected_case_id = record.case_id
        self.open_case.setEnabled(True)
        self.details.setPlainText(
            "BLACKTERM GLOBAL INTELLIGENCE DOSSIER\n\n"
            f"CASE: #{record.case_id} — {record.case_name}\n"
            f"TARGET: {record.target}\nIP: {record.ip or 'Unknown'}\n\n"
            f"APPROXIMATE LOCATION\n{record.location_text}\n"
            f"COORDINATES: {record.latitude:.4f}, {record.longitude:.4f}\n\n"
            f"INFRASTRUCTURE\nORGANIZATION: {record.organization or 'Unknown'}\n"
            f"ASN: {record.asn or 'Unknown'}\n\n"
            f"INTELLIGENCE RISK: {record.risk}/100\nCONFIDENCE: {record.confidence}%\n"
            f"COLLECTED: {record.created_at or 'Unknown'}\n\n"
            "Location data is approximate public-source intelligence and must not be treated as a physical address."
        )

    def _open_selected_case(self):
        if self.selected_case_id is not None:
            self.case_requested.emit(self.selected_case_id)
