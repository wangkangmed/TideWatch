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
                  company TEXT,
                  source_id TEXT,
                  source_type TEXT,
                  url TEXT,
                  canonical_url TEXT,
                  title TEXT,
                  published_at TEXT,
                  updated_at TEXT,
                  ingested_at TEXT,
                  doc_type TEXT,
                  content_text TEXT,
                  summary TEXT,
                  tags TEXT,
                  language TEXT,
                  access_mode TEXT,
                  fetch_status INTEGER,
                  blocked_by TEXT,
                  quality_score REAL,
                  content_hash TEXT,
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
            self._migrate(conn)

    def _migrate(self, conn: sqlite3.Connection) -> None:
        """Add columns that may be missing from older schemas."""
        existing = {row[1] for row in conn.execute("PRAGMA table_info(normalized_documents)").fetchall()}
        migrations = [
            ("company", "TEXT"),
            ("source_type", "TEXT"),
            ("canonical_url", "TEXT"),
            ("published_at", "TEXT"),
            ("updated_at", "TEXT"),
            ("ingested_at", "TEXT"),
            ("doc_type", "TEXT"),
            ("summary", "TEXT"),
            ("tags", "TEXT"),
            ("language", "TEXT"),
            ("access_mode", "TEXT"),
            ("fetch_status", "INTEGER"),
            ("blocked_by", "TEXT"),
            ("content_hash", "TEXT"),
        ]
        for col, col_type in migrations:
            if col not in existing:
                conn.execute(f"ALTER TABLE normalized_documents ADD COLUMN {col} {col_type}")

    def save_doc(self, doc: FocusedNormalizedDocument) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO normalized_documents
                (document_id, company, source_id, source_type, url, canonical_url,
                 title, published_at, updated_at, ingested_at, doc_type,
                 content_text, summary, tags, language, access_mode,
                 fetch_status, blocked_by, quality_score, content_hash, raw_metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    doc.document_id,
                    doc.company,
                    doc.source_id,
                    doc.source_type,
                    doc.url,
                    doc.canonical_url,
                    doc.title,
                    str(doc.published_at) if doc.published_at else None,
                    str(doc.updated_at) if doc.updated_at else None,
                    str(doc.ingested_at),
                    doc.doc_type,
                    doc.content_text,
                    doc.summary,
                    json.dumps(doc.tags, ensure_ascii=False) if doc.tags else None,
                    doc.language,
                    doc.access_mode,
                    doc.fetch_status,
                    doc.blocked_by,
                    doc.quality_score,
                    doc.content_hash,
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
