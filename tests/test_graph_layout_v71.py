from blackterm_recon.correlation_engine import CorrelationEdge, CorrelationNode
from blackterm_recon.graph_model import build_graph_snapshot


def nodes():
    return [
        CorrelationNode("case:1", "CASE", "Case 1", "", 0),
        CorrelationNode("domain:a", "DOMAIN", "a.test", "", 0),
        CorrelationNode("ip:1", "IP", "1.1.1.1", "", 0),
        CorrelationNode("asn:1", "ASN", "AS13335", "", 0),
    ]


def edges():
    return [
        CorrelationEdge("case:1", "domain:a", "contains", 96),
        CorrelationEdge("domain:a", "ip:1", "resolves", 92),
        CorrelationEdge("ip:1", "asn:1", "belongs", 88),
    ]


def test_cluster_layout_separates_entity_types():
    graph = build_graph_snapshot(nodes(), edges(), layout="cluster")
    xs = {node.kind: node.x for node in graph.nodes}
    assert len(set(xs.values())) == 4


def test_tree_layout_increases_depth_left_to_right():
    graph = build_graph_snapshot(nodes(), edges(), layout="tree")
    xs = {node.node_id: node.x for node in graph.nodes}
    assert xs["case:1"] < xs["domain:a"] < xs["ip:1"] < xs["asn:1"]


def test_network_layout_expands_crowded_rings():
    many = [CorrelationNode(f"domain:{i}", "DOMAIN", f"{i}.test", "", 0) for i in range(80)]
    graph = build_graph_snapshot(many, [], layout="network")
    assert max(abs(node.x) for node in graph.nodes) > 500
