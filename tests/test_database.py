from blackterm_recon.database import ScanRepository
from blackterm_recon.models import PortResult, ScanResult


def test_database_round_trip(tmp_path):
    repo = ScanRepository(str(tmp_path / "history.db"))
    result = ScanResult(
        target="127.0.0.1",
        ip="127.0.0.1",
        hostname="localhost",
        started_at="a",
        finished_at="b",
        duration_seconds=0.1,
        ports=[PortResult(port=80, state="open", service="http")],
    )
    scan_id = repo.save(result)
    loaded = repo.get(scan_id)
    assert loaded.hostname == "localhost"
    assert loaded.open_ports[0].port == 80


def test_database_migrates_old_schema(tmp_path):
    import sqlite3
    path = tmp_path / "old.db"
    conn = sqlite3.connect(path)
    conn.execute(
        """
        CREATE TABLE scans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            target TEXT NOT NULL,
            ip TEXT NOT NULL,
            started_at TEXT NOT NULL,
            finished_at TEXT NOT NULL,
            duration_seconds REAL NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE port_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_id INTEGER NOT NULL,
            port INTEGER NOT NULL,
            state TEXT NOT NULL,
            service TEXT NOT NULL,
            latency_ms REAL,
            banner TEXT,
            error TEXT
        )
        """
    )
    conn.commit()
    conn.close()
    repo = ScanRepository(str(path))
    with repo.connect() as check:
        columns = {row["name"] for row in check.execute("PRAGMA table_info(scans)")}
    assert "hostname" in columns
    assert "plugin_results_json" in columns
