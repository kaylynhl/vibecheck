"""Tiny SQLite-backed store for human-study feedback (Step 9).

Single-file DB at ``outputs/feedback.sqlite``. One thread per connection -- the
module hands out a fresh connection per call. Good enough for a class-project
demo and a ~10-person human study; not built to take real concurrent load.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_FEEDBACK_DB = REPO_ROOT / "outputs" / "feedback.sqlite"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vibe_check_id TEXT NOT NULL,
    vibe_match INTEGER,
    items_helpful INTEGER,
    playlist_match INTEGER,
    extra_json TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_feedback_vibe_check_id
    ON feedback(vibe_check_id);
"""

_init_lock = threading.Lock()
_initialised_paths: set[Path] = set()


def _ensure_schema(db_path: Path) -> None:
    """Create the feedback table on first use of ``db_path``.

    We track which paths we've already initialised in-process so we don't
    re-run the DDL on every request.
    """
    with _init_lock:
        if db_path in _initialised_paths:
            return
        db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(db_path) as conn:
            conn.executescript(_SCHEMA)
        _initialised_paths.add(db_path)


def record_feedback(
    *,
    vibe_check_id: str,
    vibe_match: int | None = None,
    items_helpful: bool | None = None,
    playlist_match: bool | None = None,
    extra: dict[str, Any] | None = None,
    db_path: Path | None = None,
) -> int:
    """Insert one feedback row and return its rowid."""
    db_path = db_path or DEFAULT_FEEDBACK_DB
    _ensure_schema(db_path)

    extra_json = json.dumps(extra) if extra else None
    now = datetime.now(timezone.utc).isoformat()

    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute(
            """
            INSERT INTO feedback
                (vibe_check_id, vibe_match, items_helpful, playlist_match,
                 extra_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                vibe_check_id,
                vibe_match,
                _bool_to_int(items_helpful),
                _bool_to_int(playlist_match),
                extra_json,
                now,
            ),
        )
        conn.commit()
        return int(cursor.lastrowid or 0)


def list_feedback(
    *, db_path: Path | None = None, limit: int = 100
) -> list[dict[str, Any]]:
    """Return the most recent ``limit`` feedback rows (newest first)."""
    db_path = db_path or DEFAULT_FEEDBACK_DB
    _ensure_schema(db_path)

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT id, vibe_check_id, vibe_match, items_helpful,
                   playlist_match, extra_json, created_at
            FROM feedback
            ORDER BY id DESC
            LIMIT ?
            """,
            (int(limit),),
        ).fetchall()

    return [
        {
            "id": row["id"],
            "vibe_check_id": row["vibe_check_id"],
            "vibe_match": row["vibe_match"],
            "items_helpful": _int_to_bool(row["items_helpful"]),
            "playlist_match": _int_to_bool(row["playlist_match"]),
            "extra": json.loads(row["extra_json"]) if row["extra_json"] else None,
            "created_at": row["created_at"],
        }
        for row in rows
    ]


def _bool_to_int(value: bool | None) -> int | None:
    if value is None:
        return None
    return 1 if value else 0


def _int_to_bool(value: int | None) -> bool | None:
    if value is None:
        return None
    return bool(value)
