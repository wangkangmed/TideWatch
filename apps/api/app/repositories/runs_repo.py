"""Run queries."""

from __future__ import annotations

import json

from .db import get_conn


def list_runs(page: int = 1, page_size: int = 20) -> tuple[list[dict], int]:
    with get_conn() as conn:
        total = conn.execute("SELECT count(*) as c FROM pipeline_runs").fetchone()["c"]
        rows = conn.execute(
            "SELECT run_id, status, topic_query, started_at, finished_at, metadata_json "
            "FROM pipeline_runs ORDER BY started_at DESC LIMIT ? OFFSET ?",
            (page_size, (page - 1) * page_size),
        ).fetchall()
    result = []
    for r in rows:
        rid = r["run_id"]
        result.append({**r, **_run_counts(rid)})
    return result, total


def get_run(run_id: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT run_id, status, topic_query, started_at, finished_at, metadata_json "
            "FROM pipeline_runs WHERE run_id = ?",
            (run_id,),
        ).fetchone()
    if not row:
        return None
    meta = {}
    if row.get("metadata_json"):
        try:
            meta = json.loads(row["metadata_json"])
        except Exception:
            pass
    return {**row, "metadata": meta, **_run_counts(run_id)}


def get_latest_run_id() -> str | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT run_id FROM pipeline_runs ORDER BY started_at DESC LIMIT 1"
        ).fetchone()
    return row["run_id"] if row else None


def _run_counts(run_id: str) -> dict:
    with get_conn() as conn:
        def _c(table: str) -> int:
            return conn.execute(f"SELECT count(*) as c FROM {table} WHERE run_id = ?", (run_id,)).fetchone()["c"]  # noqa: S608

        return {
            "document_count": _c("documents"),
            "event_count": _c("events"),
            "trend_count": _c("trend_signals"),
            "finding_count": _c("intelligence_findings"),
            "recommendation_count": _c("recommendation_items"),
            "brief_count": _c("decision_briefs"),
        }
