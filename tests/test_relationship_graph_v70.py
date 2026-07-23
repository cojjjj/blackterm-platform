import json
from blackterm_recon.relationship_graph import build_relationship_graph


class Repo:
    def list_cases(self):
        return [
            {"id": 1, "name": "Alpha", "description": "", "status": "OPEN"},
            {"id": 2, "name": "Bravo", "description": "", "status": "ACTIVE"},
        ]
    def case_scans(self, case_id):
        return [{"id": case_id, "target": f"site{case_id}.test", "ip": "1.1.1.1"}]
    def case_evidence(self, case_id):
        return [{
            "id": case_id,
            "evidence_type": "OSINT",
            "title": "OSINT package",
            "source": "BLACKTERM",
            "content": json.dumps({"asn": "AS13335", "organization": "Cloudflare", "technology": "nginx"}),
        }]


def test_cross_case_shared_entities():
    report, stats = build_relationship_graph(Repo())
    ids = {node.node_id for node in report.nodes}
    assert "entity:ip:1.1.1.1" in ids
    assert "entity:asn:as13335" in ids
    assert stats.cases == 2
    assert stats.shared_entities >= 3
    assert any(edge.relationship.startswith("share") for edge in report.edges)


def test_query_filters_cases():
    report, stats = build_relationship_graph(Repo(), "Alpha")
    assert stats.cases == 1
    assert any(node.node_id == "case:1" for node in report.nodes)
    assert not any(node.node_id == "case:2" for node in report.nodes)
