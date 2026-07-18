from blackterm_recon.events import EventLevel, EventStore, PlatformEvent


def test_event_store_stats(tmp_path):
    store = EventStore(str(tmp_path / "events.db"))
    store.save(PlatformEvent("network", "Started"))
    store.save(PlatformEvent("network", "Warning", level=EventLevel.WARNING))
    store.save(PlatformEvent("platform", "Error", level=EventLevel.ERROR))
    store.save(PlatformEvent("ai", "Analysis", level=EventLevel.AI))
    stats = store.stats()
    assert stats["total"] == 4
    assert stats["warnings"] == 1
    assert stats["errors"] == 1
    assert stats["ai"] == 1


def test_recent_counts_returns_data(tmp_path):
    store = EventStore(str(tmp_path / "events.db"))
    store.save(PlatformEvent("platform", "Ready"))
    assert store.recent_counts()
