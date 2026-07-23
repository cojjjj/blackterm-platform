from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox, QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton, QSlider, QVBoxLayout, QWidget
)

from ...relationship_graph import build_relationship_graph
from ..investigation_graph import InvestigationGraph


class MetricCard(QFrame):
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setObjectName("metricCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 9, 12, 9)
        label = QLabel(title)
        label.setObjectName("metricLabel")
        self.value = QLabel("0")
        self.value.setObjectName("metricValue")
        layout.addWidget(label)
        layout.addWidget(self.value)


class RelationshipGraphPage(QWidget):
    case_requested = Signal(int)
    global_map_requested = Signal()

    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.selected_node = None

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(10)

        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("INVESTIGATION RELATIONSHIP GRAPH")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Cross-case entities, infrastructure overlap, evidence, and intelligence relationships.")
        subtitle.setObjectName("pageSubtitle")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header.addLayout(title_box)
        header.addStretch()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search case, target, IP, ASN, organization...")
        self.search.setMinimumWidth(380)
        self.search.returnPressed.connect(self.refresh)
        refresh = QPushButton("REFRESH GRAPH")
        refresh.clicked.connect(self.refresh)
        header.addWidget(self.search)
        header.addWidget(refresh)
        root.addLayout(header)

        metrics = QHBoxLayout()
        self.case_metric = MetricCard("CASES")
        self.entity_metric = MetricCard("ENTITIES")
        self.link_metric = MetricCard("RELATIONSHIPS")
        self.shared_metric = MetricCard("SHARED ENTITIES")
        for card in (self.case_metric, self.entity_metric, self.link_metric, self.shared_metric):
            metrics.addWidget(card)
        root.addLayout(metrics)

        self.graph = InvestigationGraph(self)
        self.graph.node_selected.connect(self._node_selected)
        self.search.textChanged.connect(self.graph.highlight)

        controls = QHBoxLayout()
        controls.addWidget(QLabel("VIEW"))
        self.view_mode = QComboBox()
        self.view_mode.addItem("EXPLORE", "explore")
        self.view_mode.addItem("NETWORK", "network")
        self.view_mode.addItem("CLUSTER", "cluster")
        self.view_mode.addItem("TREE", "tree")
        self.view_mode.setCurrentIndex(0)
        self.view_mode.currentIndexChanged.connect(
            lambda _index: self.graph.set_layout_mode(self.view_mode.currentData())
        )
        controls.addWidget(self.view_mode)
        controls.addSpacing(16)
        controls.addWidget(QLabel("RELATIONSHIP STRENGTH"))
        self.strength = QSlider(Qt.Horizontal)
        self.strength.setRange(0, 100)
        self.strength.setValue(85)
        self.strength.setSingleStep(5)
        self.strength.setMinimumWidth(220)
        self.strength_value = QLabel("85%+")
        self.strength.valueChanged.connect(self._strength_changed)
        controls.addWidget(self.strength, 1)
        controls.addWidget(self.strength_value)
        self.focus_button = QPushButton("FOCUS SELECTED")
        self.focus_button.setEnabled(False)
        self.focus_button.clicked.connect(self._focus_selected)
        self.auto_layout_button = QPushButton("AUTO LAYOUT")
        self.auto_layout_button.clicked.connect(self._auto_layout)
        self.clear_focus_button = QPushButton("SHOW ALL")
        self.clear_focus_button.clicked.connect(self._clear_focus)
        controls.addWidget(self.auto_layout_button)
        controls.addWidget(self.focus_button)
        controls.addWidget(self.clear_focus_button)
        root.addLayout(controls)
        root.addWidget(self.graph, 1)

        actions = QHBoxLayout()
        self.open_case = QPushButton("OPEN LINKED CASE")
        self.open_case.setEnabled(False)
        self.open_case.clicked.connect(self._open_case)
        self.open_map = QPushButton("SHOW ON GLOBAL MAP")
        self.open_map.clicked.connect(self.global_map_requested.emit)
        self.context = QLabel("Select a case or entity node to inspect its relationship context.")
        self.context.setWordWrap(True)
        actions.addWidget(self.context, 1)
        actions.addWidget(self.open_case)
        actions.addWidget(self.open_map)
        root.addLayout(actions)

        self.refresh()

    def refresh(self):
        report, stats = build_relationship_graph(self.engine.repository, self.search.text())
        self.graph.set_report(report)
        self.case_metric.value.setText(str(stats.cases))
        self.entity_metric.value.setText(str(stats.entities))
        self.link_metric.value.setText(str(stats.relationships))
        self.shared_metric.value.setText(str(stats.shared_entities))
        if not report.nodes:
            self.graph.detail.setText("No matching case intelligence is available yet. Run or save an investigation, then refresh the graph.")

    def _node_selected(self, node):
        self.selected_node = node
        self.open_case.setEnabled(self.graph.linked_case_id(node.node_id) is not None)
        self.focus_button.setEnabled(True)
        self.context.setText(f"{node.kind} // {node.label}\n{node.detail or 'No additional context recorded.'}")

    def _strength_changed(self, value: int):
        self.strength_value.setText(f"{value}%+")
        self.graph.set_edge_threshold(value)

    def _auto_layout(self):
        mode = self.graph.auto_layout()
        index = self.view_mode.findData(mode)
        if index >= 0:
            self.view_mode.blockSignals(True)
            self.view_mode.setCurrentIndex(index)
            self.view_mode.blockSignals(False)
        self.context.setText(
            f"AUTO LAYOUT // {mode.upper()}\n"
            "BLACKTERM selected the layout best suited to the current graph density."
        )

    def _focus_selected(self):
        if self.selected_node:
            self.graph.focus_node(self.selected_node.node_id)
            self.context.setText(
                f"FOCUSED // {self.selected_node.kind} // {self.selected_node.label}\n"
                "Showing direct relationships only. Select SHOW ALL to restore the full graph."
            )

    def _clear_focus(self):
        self.graph.clear_focus()
        self.graph.highlight(self.search.text())
        self.context.setText("Full relationship graph restored.")

    def _open_case(self):
        if not self.selected_node:
            return
        case_id = self.graph.linked_case_id(self.selected_node.node_id)
        if case_id is not None:
            self.case_requested.emit(case_id)
