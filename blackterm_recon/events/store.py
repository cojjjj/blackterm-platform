from __future__ import annotations

from pathlib import Path
from typing import Iterable
import json
import sqlite3

from .models import EventLevel, PlatformEvent


SCHEMA = """
CREATE TABLE IF NOT EXISTS platform_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT NOT NULL UNIQUE,
    timestamp TEXT NOT NULL,
    level TEXT NOT NULL,
    category TEXT NOT NULL,
    module TEXT NOT NULL,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    scan_id INTEGER,
    metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_platform_events_time
ON platform_events(timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_platform_events_category
ON platform_events(category);

CREATE INDEX IF NOT EXISTS idx_platform_events_level
ON platform_events(level);
"""


class EventStore:
    def __init__(self, database_path: str):
        self.path = Path(database_path).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def connect(self):
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(SCHEMA)
            connection.commit()

    def save(self, event: PlatformEvent) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO platform_events (
                    event_id, timestamp, level, category, module,
                    title, message, scan_id, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.event_id,
                    event.timestamp,
                    event.level.value,
                    event.category,
                    event.module,
                    event.title,
                    event.message,
                    event.scan_id,
                    json.dumps(event.metadata),
                ),
            )
            connection.commit()

    def recent(
        self,
        limit: int = 250,
        category: str | None = None,
        level: str | None = None,
        search: str | None = None,
    ) -> list[PlatformEvent]:
        clauses = []
        values: list[object] = []
        if category and category != "all":
            clauses.append("category = ?")
            values.append(category)
        if level and level != "all":
            clauses.append("level = ?")
            values.append(level)
        if search:
            clauses.append("(title LIKE ? OR message LIKE ?)")
            needle = f"%{search}%"
            values.extend([needle, needle])

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        values.append(limit)
        with self.connect() as connection:
            rows = connection.execute(
                f"""
                SELECT * FROM platform_events
                {where}
                ORDER BY id DESC
                LIMIT ?
                """,
                tuple(values),
            ).fetchall()

        output = []
        for row in reversed(rows):
            output.append(
                PlatformEvent(
                    event_id=row["event_id"],
                    timestamp=row["timestamp"],
                    level=EventLevel(row["level"]),
                    category=row["category"],
                    module=row["module"],
                    title=row["title"],
                    message=row["message"],
                    scan_id=row["scan_id"],
                    metadata=json.loads(row["metadata_json"] or "{}"),
                )
            )
        return output

    def categories(self) -> list[str]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT DISTINCT category FROM platform_events ORDER BY category"
            ).fetchall()
        return [row["category"] for row in rows]


    def stats(self) -> dict:
        with self.connect() as connection:
            total = connection.execute(
                "SELECT COUNT(*) AS count FROM platform_events"
            ).fetchone()["count"]
            warnings = connection.execute(
                "SELECT COUNT(*) AS count FROM platform_events WHERE level='warning'"
            ).fetchone()["count"]
            errors = connection.execute(
                "SELECT COUNT(*) AS count FROM platform_events WHERE level='error'"
            ).fetchone()["count"]
            ai = connection.execute(
                "SELECT COUNT(*) AS count FROM platform_events WHERE level='ai'"
            ).fetchone()["count"]
            scans = connection.execute(
                "SELECT COUNT(*) AS count FROM platform_events WHERE title='Scan Complete'"
            ).fetchone()["count"]
        return {
            "total": total,
            "warnings": warnings,
            "errors": errors,
            "ai": ai,
            "completed_scans": scans,
        }

    def recent_counts(self, limit: int = 24) -> list[int]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT substr(timestamp, 1, 13) AS bucket, COUNT(*) AS count
                FROM platform_events
                GROUP BY bucket
                ORDER BY bucket DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return list(reversed([row["count"] for row in rows])) or [0]

    def clear(self) -> None:
        with self.connect() as connection:
            connection.execute("DELETE FROM platform_events")
            connection.commit()
