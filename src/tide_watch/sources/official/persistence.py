"""Persistence layer for focused ingestion (subgraph-local)."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from tide_watch.models.ingestion import FetchAttempt, FocusedNormalizedDocument, SourceHealth


class IngestionRepository:
    def __init__(self, db_path: str | None = None) -> None:
        base = Path(db_path) if db_path else Path(__file__).resolve().parents[4] / "data" / "ingestion.sqlite3"
        if str(base) != ":memory:":
            base.parent.mkdir(parents=True, exist_ok=True)
        self.db_path = str(base)
        self._init()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _init(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS normalized_documents (
                  document_id TEXT PRIMARY KEY,
                  source_id TEXT,
                  url TEXT,
                  title TEXT,
                  content_text TEXT,
                  quality_score REAL,
                  raw_metadata TEXT
                );
                CREATE TABLE IF NOT EXISTS fetch_attempts (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  source_id TEXT,
                  url TEXT,
                  status_code INTEGER,
                  block_type TEXT,
                  fetch_mode TEXT,
                  retryable INTEGER,
                  error TEXT,
                  created_at TEXT
                );
                CREATE TABLE IF NOT EXISTS source_health (
                  source_id TEXT PRIMARY KEY,
                  payload TEXT
                );
                """
            )

    def save_doc(self, doc: FocusedNormalizedDocument) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO normalized_documents
                (document_id, source_id, url, title, content_text, quality_score, raw_metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    doc.document_id,
                    doc.source_id,
                    doc.url,
                    doc.title,
                    doc.content_text,
                    doc.quality_score,
                    json.dumps(doc.raw_metadata, ensure_ascii=False),
                ),
            )

    def save_attempt(self, attempt: FetchAttempt) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO fetch_attempts (source_id, url, status_code, block_type, fetch_mode, retryable, error, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    attempt.source_id,
                    attempt.url,
                    attempt.status_code,
                    attempt.block_type,
                    attempt.fetch_mode,
                    1 if attempt.retryable else 0,
                    attempt.error,
                    str(attempt.created_at),
                ),
            )

    def load_health(self) -> dict[str, SourceHealth]:
        out: dict[str, SourceHealth] = {}
        with self._connect() as conn:
            rows = conn.execute("SELECT source_id, payload FROM source_health").fetchall()
            for source_id, payload in rows:
                data = json.loads(payload)
                if hasattr(SourceHealth, "model_validate"):
                    out[source_id] = SourceHealth.model_validate(data)
                else:
                    out[source_id] = SourceHealth.parse_obj(data)
        return out

    def save_health(self, health: dict[str, SourceHealth]) -> None:
        with self._connect() as conn:
            for source_id, item in health.items():
                payload = item.model_dump(mode="json") if hasattr(item, "model_dump") else item.dict()
                conn.execute(
                    "INSERT OR REPLACE INTO source_health (source_id, payload) VALUES (?, ?)",
                    (source_id, json.dumps(payload, ensure_ascii=False)),
                )
