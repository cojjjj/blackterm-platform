from blackterm_recon.events import EventLevel, EventStore, PlatformEvent


def test_event_store_filters(tmp_path):
    store = EventStore(str(tmp_path / "events.db"))
    store.save(PlatformEvent("network", "Scan started"))
    store.save(PlatformEvent("ai", "Analysis ready", level=EventLevel.AI))
    store.save(PlatformEvent("network", "Scan failed", level=EventLevel.ERROR))

    assert len(store.recent(category="network")) == 2
    assert len(store.recent(level="ai")) == 1
    assert len(store.recent(search="failed")) == 1


def test_event_store_clear(tmp_path):
    store = EventStore(str(tmp_path / "events.db"))
    store.save(PlatformEvent("platform", "Ready"))
    store.clear()
    assert store.recent() == []
