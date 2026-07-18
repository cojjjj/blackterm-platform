from blackterm_recon.events import EventBus, EventLevel, EventStore


def test_event_bus_publishes_and_persists(tmp_path):
    store = EventStore(str(tmp_path / "events.db"))
    bus = EventBus(store)
    received = []
    bus.subscribe(received.append)

    event = bus.emit(
        "network",
        "Port responded",
        title="Open Port",
        level=EventLevel.SUCCESS,
        metadata={"port": 443},
    )

    assert received[0].event_id == event.event_id
    saved = store.recent()
    assert saved[0].metadata["port"] == 443


def test_event_bus_category_subscription(tmp_path):
    bus = EventBus(EventStore(str(tmp_path / "events.db")))
    received = []
    bus.subscribe(received.append, "ai")
    bus.emit("network", "Network")
    bus.emit("ai", "Assistant response", level=EventLevel.AI)
    assert len(received) == 1
    assert received[0].category == "ai"
