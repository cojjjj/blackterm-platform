from contextlib import contextmanager
from pathlib import Path
import json
import sqlite3

from .models import PortResult, ScanResult, TechnologyFingerprint


SCHEMA_VERSION = 8

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
    plugin_results_json TEXT NOT NULL DEFAULT '{}',
    operation_id TEXT,
    profile TEXT NOT NULL DEFAULT 'custom',
    attack_surface_json TEXT NOT NULL DEFAULT '{}'
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



CREATE TABLE IF NOT EXISTS case_evidence (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    evidence_type TEXT NOT NULL,
    title TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT '',
    content TEXT NOT NULL DEFAULT '',
    file_path TEXT NOT NULL DEFAULT '',
    sha256 TEXT NOT NULL DEFAULT '',
    FOREIGN KEY(case_id) REFERENCES cases(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS case_timeline (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    event_type TEXT NOT NULL,
    title TEXT NOT NULL,
    detail TEXT NOT NULL DEFAULT '',
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
                "operation_id": "ALTER TABLE scans ADD COLUMN operation_id TEXT",
                "profile": "ALTER TABLE scans ADD COLUMN profile TEXT NOT NULL DEFAULT 'custom'",
                "attack_surface_json": "ALTER TABLE scans ADD COLUMN attack_surface_json TEXT NOT NULL DEFAULT '{}'",
                "fingerprints_json": "ALTER TABLE scans ADD COLUMN fingerprints_json TEXT NOT NULL DEFAULT '[]'",
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
                    duration_seconds, plugin_results_json, operation_id, profile,
                    attack_surface_json, fingerprints_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result.target, result.ip, result.hostname, result.started_at,
                    result.finished_at, result.duration_seconds,
                    json.dumps(result.plugin_results), result.operation_id, result.profile,
                    json.dumps(result.attack_surface),
                    json.dumps([item.to_dict() for item in result.fingerprints]),
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
            operation_id=scan["operation_id"] if "operation_id" in scan.keys() else None,
            profile=scan["profile"] if "profile" in scan.keys() else "custom",
            attack_surface=json.loads(scan["attack_surface_json"] or "{}") if "attack_surface_json" in scan.keys() else {},
            fingerprints=[
                TechnologyFingerprint(**item)
                for item in (json.loads(scan["fingerprints_json"] or "[]") if "fingerprints_json" in scan.keys() else [])
            ],
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
            case_id = int(cursor.lastrowid)
        self.add_case_timeline(case_id, "CASE", "Investigation created", description.strip())
        return case_id

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
        self.add_case_timeline(case_id, "SCAN", f"Scan #{scan_id} attached")

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
            note_id = int(cursor.lastrowid)
        self.add_case_timeline(case_id, "NOTE", "Investigation note added", note.strip()[:240])
        return note_id

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


    def update_case_status(self, case_id: int, status: str) -> None:
        allowed = {"OPEN", "ACTIVE", "REVIEW", "CLOSED"}
        status = status.upper()
        if status not in allowed:
            raise ValueError(f"Unsupported case status: {status}")
        with self.connect() as conn:
            conn.execute("UPDATE cases SET status=? WHERE id=?", (status, case_id))
        self.add_case_timeline(case_id, "STATUS", f"Status changed to {status}")

    def add_case_evidence(self, case_id: int, evidence_type: str, title: str,
                          source: str = "", content: str = "", file_path: str = "") -> int:
        from datetime import datetime, timezone
        from hashlib import sha256
        digest_source = content.encode("utf-8", errors="replace")
        if file_path:
            try:
                digest_source = Path(file_path).expanduser().read_bytes()
            except OSError:
                pass
        digest = sha256(digest_source).hexdigest()
        with self.connect() as conn:
            cursor = conn.execute(
                """INSERT INTO case_evidence(
                    case_id, created_at, evidence_type, title, source,
                    content, file_path, sha256
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (case_id, datetime.now(timezone.utc).isoformat(), evidence_type.upper(),
                 title.strip(), source.strip(), content, file_path, digest),
            )
            evidence_id = int(cursor.lastrowid)
        self.add_case_timeline(case_id, "EVIDENCE", f"Evidence added: {title}", evidence_type.upper())
        return evidence_id

    def case_evidence(self, case_id: int) -> list[dict]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM case_evidence WHERE case_id=? ORDER BY id DESC", (case_id,)
            ).fetchall()
        return [dict(row) for row in rows]

    def add_case_timeline(self, case_id: int, event_type: str, title: str, detail: str = "") -> int:
        from datetime import datetime, timezone
        with self.connect() as conn:
            cursor = conn.execute(
                """INSERT INTO case_timeline(case_id, created_at, event_type, title, detail)
                   VALUES (?, ?, ?, ?, ?)""",
                (case_id, datetime.now(timezone.utc).isoformat(), event_type.upper(), title, detail),
            )
            return int(cursor.lastrowid)

    def case_timeline(self, case_id: int) -> list[dict]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM case_timeline WHERE case_id=? ORDER BY id ASC", (case_id,)
            ).fetchall()
        return [dict(row) for row in rows]

    def search_cases(self, query: str) -> list[dict]:
        pattern = f"%{query.strip()}%"
        with self.connect() as conn:
            rows = conn.execute(
                """SELECT DISTINCT c.id, c.name, c.description, c.created_at, c.status,
                          (SELECT COUNT(*) FROM case_scans cs WHERE cs.case_id=c.id) AS scan_count
                   FROM cases c
                   LEFT JOIN case_notes n ON n.case_id=c.id
                   LEFT JOIN case_evidence e ON e.case_id=c.id
                   WHERE c.name LIKE ? OR c.description LIKE ? OR n.note LIKE ?
                      OR e.title LIKE ? OR e.content LIKE ?
                   ORDER BY c.id DESC""",
                (pattern, pattern, pattern, pattern, pattern),
            ).fetchall()
        return [dict(row) for row in rows]
