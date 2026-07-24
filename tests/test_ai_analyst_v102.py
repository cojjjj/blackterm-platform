from blackterm_recon.assistant_engine import answer_question, build_analyst_brief
from blackterm_recon.models import PortResult, ScanResult, TechnologyFingerprint


def sample_result():
    return ScanResult(
        target="lab.example",
        ip="192.0.2.10",
        hostname="lab.example",
        started_at="a",
        finished_at="b",
        duration_seconds=0.2,
        profile="standard",
        ports=[
            PortResult(port=22, state="open", service="ssh"),
            PortResult(port=443, state="open", service="https"),
            PortResult(port=445, state="open", service="microsoft-ds"),
        ],
        fingerprints=[TechnologyFingerprint(name="Nginx", confidence=90)],
    )


def test_brief_separates_facts_and_inferences():
    brief = build_analyst_brief(sample_result())
    assert brief.target == "lab.example"
    assert brief.facts
    assert brief.inferences
    assert brief.confidence > 0
    assert brief.evidence_count >= 3
    assert any("TCP/445" in fact for fact in brief.facts)


def test_executive_brief_intent():
    reply = answer_question("generate executive brief", sample_result())
    assert reply.intent == "brief"
    assert "CONFIRMED FACTS" in reply.body
    assert "ANALYST INFERENCES" in reply.body
    assert reply.confidence > 0


def test_risk_answer_preserves_non_vulnerability_language():
    reply = answer_question("why is this risky", sample_result())
    assert reply.intent == "assessment"
    assert "No vulnerability is established" in reply.body


def test_fact_and_inference_queries_are_distinct():
    facts = answer_question("what do we know", sample_result())
    inference = answer_question("what might this suggest", sample_result())
    assert facts.intent == "facts"
    assert inference.intent == "inferences"
    assert "confirmed vulnerabilities" in inference.body
