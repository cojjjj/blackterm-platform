from blackterm_recon.graph_model import build_graph_snapshot


def test_live_graph_snapshot_preserves_nodes_and_edges():
    nodes = [
        {"node_id": "case:1", "kind": "CASE", "label": "Case #1", "detail": "", "risk": 0},
        {"node_id": "target:a", "kind": "TARGET", "label": "example.test", "detail": "", "risk": 0},
    ]
    edges = [
        {"source": "case:1", "target": "target:a", "relationship": "contains", "confidence": 90}
    ]
    snapshot = build_graph_snapshot(nodes, edges)
    assert len(snapshot.nodes) == 2
    assert len(snapshot.edges) == 1
