from blackterm_recon.events.bus import EventBus
from blackterm_recon.events.models import PlatformEvent
from blackterm_recon.investigation_engine import assess_result


def test_event_bus_tokens_and_history():
    bus = EventBus(history_size=12)
    seen = []
    token = bus.subscribe(seen.append)
    event = PlatformEvent(category="test", message="hello")
    bus.publish(event)
    assert seen == [event]
    assert bus.recent(1) == [event]
    bus.unsubscribe(token)
    bus.publish(PlatformEvent(category="test", message="again"))
    assert len(seen) == 1


def test_ai_assessment_contains_confidence_and_findings():
    port = type("Port", (), {"port": 445, "service": "microsoft-ds"})()
    result = type("Result", (), {"target": "127.0.0.1", "open_ports": [port]})()
    assessment = assess_result(result)
    assert assessment.confidence >= 50
    assert assessment.findings
    assert "CONFIDENCE" in assessment.to_text()
