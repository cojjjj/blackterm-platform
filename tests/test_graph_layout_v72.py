from blackterm_recon.graph_model import build_graph_snapshot


def _nodes(count=120):
    kinds = ["CASE", "DOMAIN", "IP", "ASN", "ORGANIZATION", "TECHNOLOGY"]
    return [
        {"node_id": f"n:{i}", "kind": kinds[i % len(kinds)], "label": f"node-{i}", "detail": "", "risk": 0}
        for i in range(count)
    ]


def test_cluster_layout_uses_both_axes_for_large_graphs():
    snapshot = build_graph_snapshot(_nodes(), [], layout="cluster")
    xs = [node.x for node in snapshot.nodes]
    ys = [node.y for node in snapshot.nodes]
    assert max(xs) - min(xs) > 900
    assert max(ys) - min(ys) > 500


def test_cluster_layout_positions_are_not_collapsed():
    snapshot = build_graph_snapshot(_nodes(60), [], layout="cluster")
    positions = {(round(node.x, 2), round(node.y, 2)) for node in snapshot.nodes}
    assert len(positions) == len(snapshot.nodes)
