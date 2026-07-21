from __future__ import annotations

from datetime import datetime, timezone
import secrets


def new_operation_id(now: datetime | None = None) -> str:
    """Return a human-readable, collision-resistant operation identifier."""
    stamp = (now or datetime.now(timezone.utc)).strftime("%Y%m%d-%H%M%S")
    suffix = secrets.token_hex(2).upper()
    return f"BT-{stamp}-{suffix}"
