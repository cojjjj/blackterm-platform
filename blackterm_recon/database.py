from contextlib import contextmanager
from pathlib import Path
import json
import sqlite3

from .models import PortResult, ScanResult


SCHEMA_VERSION = 5

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS scans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    target TEXT NOT NULL,
    ip TEXT NOT NULL,
    hostname TEXT,
    started_at TEXT NOT NULL,
    finished_at TEXT NOT NULL,
    duration_seconds REAL NOT NULL,
    plugin_results_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS cases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'OPEN'
);

CREATE TABLE IF NOT EXISTS case_scans (
    case_id INTEGER NOT NULL,
    scan_id INTEGER NOT NULL,
    PRIMARY KEY(case_id, scan_id),
    FOREIGN KEY(case_id) REFERENCES cases(id) ON DELETE CASCADE,
    FOREIGN KEY(scan_id) REFERENCES scans(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS case_notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    note TEXT NOT NULL,
    FOREIGN KEY(case_id) REFERENCES cases(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS scan_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_id INTEGER NOT NULL,
    event_time TEXT NOT NULL,
    event_type TEXT NOT NULL,
    message TEXT NOT NULL,
    FOREIGN KEY(scan_id) REFERENCES scans(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS port_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_id INTEGER NOT NULL,
    port INTEGER NOT NULL,
    state TEXT NOT NULL,
    service TEXT NOT NULL,
    latency_ms REAL,
    banner TEXT,
    error TEXT,
    FOREIGN KEY(scan_id) REFERENCES scans(id) ON DELETE CASCADE
);
"""


class ScanRepository:
    def __init__(self, database_path: str):
        self.path = Path(database_path).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    @contextmanager
    def connect(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _columns(self, conn, table: str) -> set[str]:
        return {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}

    def initialize(self):
        with self.connect() as conn:
            conn.executescript(SCHEMA)
            columns = self._columns(conn, "scans")
            migrations = {
                "hostname": "ALTER TABLE scans ADD COLUMN hostname TEXT",
                "plugin_results_json": "ALTER TABLE scans ADD COLUMN plugin_results_json TEXT NOT NULL DEFAULT '{}'",
            }
            for column, statement in migrations.items():
                if column not in columns:
                    conn.execute(statement)
            conn.execute(
                "INSERT OR REPLACE INTO schema_meta(key, value) VALUES('version', ?)",
                (str(SCHEMA_VERSION),),
            )

    def save(self, result: ScanResult) -> int:
        with self.connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO scans (
                    target, ip, hostname, started_at, finished_at,
                    duration_seconds, plugin_results_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result.target, result.ip, result.hostname, result.started_at,
                    result.finished_at, result.duration_seconds,
                    json.dumps(result.plugin_results),
                ),
            )
            scan_id = int(cursor.lastrowid)
            conn.executemany(
                """
                INSERT INTO port_results (
                    scan_id, port, state, service, latency_ms, banner, error
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (scan_id, p.port, p.state, p.service, p.latency_ms, p.banner, p.error)
                    for p in result.ports
                ],
            )
            return scan_id

    def list_recent(self, limit: int = 100) -> list[dict]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT s.id, s.target, s.ip, s.hostname, s.finished_at,
                       s.duration_seconds,
                       SUM(CASE WHEN p.state='open' THEN 1 ELSE 0 END) AS open_ports
                FROM scans s
                LEFT JOIN port_results p ON p.scan_id=s.id
                GROUP BY s.id
                ORDER BY s.id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def get(self, scan_id: int) -> ScanResult | None:
        with self.connect() as conn:
            scan = conn.execute("SELECT * FROM scans WHERE id=?", (scan_id,)).fetchone()
            if scan is None:
                return None
            ports = conn.execute(
                "SELECT * FROM port_results WHERE scan_id=? ORDER BY port",
                (scan_id,),
            ).fetchall()

        return ScanResult(
            target=scan["target"],
            ip=scan["ip"],
            hostname=scan["hostname"],
            started_at=scan["started_at"],
            finished_at=scan["finished_at"],
            duration_seconds=scan["duration_seconds"],
            plugin_results=json.loads(scan["plugin_results_json"] or "{}"),
            ports=[
                PortResult(
                    port=p["port"], state=p["state"], service=p["service"],
                    latency_ms=p["latency_ms"], banner=p["banner"], error=p["error"],
                )
                for p in ports
            ],
        )


    def create_case(self, name: str, description: str = "") -> int:
        from datetime import datetime, timezone
        with self.connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO cases(name, description, created_at, status)
                VALUES (?, ?, ?, 'OPEN')
                """,
                (name.strip(), description.strip(), datetime.now(timezone.utc).isoformat()),
            )
            return int(cursor.lastrowid)

    def list_cases(self) -> list[dict]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT c.id, c.name, c.description, c.created_at, c.status,
                       COUNT(cs.scan_id) AS scan_count
                FROM cases c
                LEFT JOIN case_scans cs ON cs.case_id = c.id
                GROUP BY c.id
                ORDER BY c.id DESC
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def attach_scan_to_case(self, case_id: int, scan_id: int) -> None:
        with self.connect() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO case_scans(case_id, scan_id) VALUES (?, ?)",
                (case_id, scan_id),
            )

    def case_scans(self, case_id: int) -> list[dict]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT s.id, s.target, s.ip, s.hostname, s.finished_at,
                       SUM(CASE WHEN p.state='open' THEN 1 ELSE 0 END) AS open_ports
                FROM case_scans cs
                JOIN scans s ON s.id = cs.scan_id
                LEFT JOIN port_results p ON p.scan_id = s.id
                WHERE cs.case_id = ?
                GROUP BY s.id
                ORDER BY s.id DESC
                """,
                (case_id,),
            ).fetchall()
        return [dict(row) for row in rows]


    def add_case_note(self, case_id: int, note: str) -> int:
        from datetime import datetime, timezone
        with self.connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO case_notes(case_id, created_at, note)
                VALUES (?, ?, ?)
                """,
                (case_id, datetime.now(timezone.utc).isoformat(), note.strip()),
            )
            return int(cursor.lastrowid)

    def case_notes(self, case_id: int) -> list[dict]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT id, created_at, note
                FROM case_notes
                WHERE case_id=?
                ORDER BY id DESC
                """,
                (case_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def save_events(self, scan_id: int, events: list[tuple[str, str, str]]) -> None:
        if not events:
            return
        with self.connect() as conn:
            conn.executemany(
                """
                INSERT INTO scan_events(scan_id, event_time, event_type, message)
                VALUES (?, ?, ?, ?)
                """,
                [(scan_id, event_time, event_type, message) for event_time, event_type, message in events],
            )

    def get_events(self, scan_id: int) -> list[dict]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT event_time, event_type, message
                FROM scan_events
                WHERE scan_id=?
                ORDER BY id
                """,
                (scan_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def stats(self) -> dict:
        with self.connect() as conn:
            scans = conn.execute("SELECT COUNT(*) AS count FROM scans").fetchone()["count"]
            open_ports = conn.execute(
                "SELECT COUNT(*) AS count FROM port_results WHERE state='open'"
            ).fetchone()["count"]
            last = conn.execute(
                "SELECT finished_at FROM scans ORDER BY id DESC LIMIT 1"
            ).fetchone()
        return {
            "scans": scans,
            "open_ports": open_ports,
            "last_scan": last["finished_at"] if last else "Never",
        }
