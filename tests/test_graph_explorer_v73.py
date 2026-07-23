from blackterm_recon.graph_model import build_graph_snapshot


def test_explore_layout_places_case_roots_apart():
    nodes = [
        {"node_id": "case:1", "kind": "CASE", "label": "Case 1", "detail": "", "risk": 0},
        {"node_id": "case:2", "kind": "CASE", "label": "Case 2", "detail": "", "risk": 0},
    ]
    snapshot = build_graph_snapshot(nodes, [], layout="explore")
    assert len(snapshot.nodes) == 2
    assert abs(snapshot.nodes[0].x - snapshot.nodes[1].x) >= 600


def test_explore_layout_places_neighbors_radially():
    nodes = [
        {"node_id": "case:1", "kind": "CASE", "label": "Case 1", "detail": "", "risk": 0},
        {"node_id": "domain:1", "kind": "DOMAIN", "label": "example.com", "detail": "", "risk": 0},
        {"node_id": "ip:1", "kind": "IP", "label": "203.0.113.10", "detail": "", "risk": 0},
    ]
    edges = [
        {"source": "case:1", "target": "domain:1", "relationship": "contains", "confidence": 95},
        {"source": "case:1", "target": "ip:1", "relationship": "contains", "confidence": 95},
    ]
    snapshot = build_graph_snapshot(nodes, edges, layout="explore")
    positions = {node.node_id: (node.x, node.y) for node in snapshot.nodes}
    assert positions["case:1"] != positions["domain:1"]
    assert positions["case:1"] != positions["ip:1"]
    assert positions["domain:1"] != positions["ip:1"]
