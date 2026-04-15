"""Lightweight SQLite connection pool for read-only access."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from typing import Iterator

from ..config import DB_PATH


def _row_factory(cursor: sqlite3.Cursor, row: tuple) -> dict:
    cols = [col[0] for col in cursor.description]
    return dict(zip(cols, row))


@contextmanager
def get_conn(db_path: str | None = None) -> Iterator[sqlite3.Connection]:
    path = db_path or DB_PATH
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = _row_factory
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA query_only=ON")
    try:
        yield conn
    finally:
        conn.close()
