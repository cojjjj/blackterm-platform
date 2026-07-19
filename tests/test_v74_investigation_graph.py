from blackterm_recon.graph_model import build_graph_snapshot


class Node:
    def __init__(self, node_id, kind, label, detail="", risk=0):
        self.node_id = node_id
        self.kind = kind
        self.label = label
        self.detail = detail
        self.risk = risk


class Edge:
    def __init__(self, source, target, relationship, confidence=70):
        self.source = source
        self.target = target
        self.relationship = relationship
        self.confidence = confidence


def test_graph_snapshot_positions_case_at_center_and_services_outward():
    snapshot = build_graph_snapshot(
        [
            Node("case:1", "CASE", "Case #1"),
            Node("scan:1", "SCAN", "Scan #1"),
            Node("target:a", "TARGET", "example.test"),
            Node("service:445", "SERVICE", "TCP/445 SMB", risk=20),
        ],
        [
            Edge("case:1", "scan:1", "contains", 100),
            Edge("scan:1", "target:a", "observed", 95),
            Edge("target:a", "service:445", "exposes", 90),
        ],
    )
    by_id = {node.node_id: node for node in snapshot.nodes}
    assert by_id["case:1"].x == 0
    assert by_id["case:1"].y == 0
    assert abs(by_id["service:445"].x) + abs(by_id["service:445"].y) > 400
    assert len(snapshot.edges) == 3


def test_graph_snapshot_drops_invalid_and_duplicate_edges():
    snapshot = build_graph_snapshot(
        [Node("case:1", "CASE", "Case #1"), Node("scan:1", "SCAN", "Scan #1")],
        [
            Edge("case:1", "scan:1", "contains"),
            Edge("case:1", "scan:1", "contains"),
            Edge("missing", "scan:1", "contains"),
        ],
    )
    assert len(snapshot.edges) == 1
