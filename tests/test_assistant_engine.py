from blackterm_recon.assistant_engine import answer_question
from blackterm_recon.models import PortResult, ScanResult


def result():
    return ScanResult(
        target="127.0.0.1",
        ip="127.0.0.1",
        hostname="localhost",
        started_at="a",
        finished_at="b",
        duration_seconds=0.1,
        ports=[
            PortResult(port=135, state="open", service="epmap"),
            PortResult(port=445, state="open", service="microsoft-ds"),
        ],
    )


def test_ports_intent():
    reply = answer_question("what ports are open", result())
    assert reply.intent == "ports"
    assert "445/tcp" in reply.body


def test_smb_intent():
    reply = answer_question("explain smb", result())
    assert reply.intent == "smb"
    assert "file and printer sharing" in reply.body


def test_assessment_intent():
    reply = answer_question("should i worry", result())
    assert reply.intent == "assessment"
    assert "No vulnerability" in reply.body
