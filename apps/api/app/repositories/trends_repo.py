"""Trend queries."""

from __future__ import annotations

import json

from .db import get_conn


_SORT_MAP = {
    "strength": "json_extract(trend_json, '$.strength_score') DESC",
    "novelty": "json_extract(trend_json, '$.novelty_score') DESC",
    "corroboration": "json_extract(trend_json, '$.corroboration_score') DESC",
    "created_at": "created_at DESC",
}


def list_trends(
    *,
    run_id: str | None = None,
    subject: str | None = None,
    theme: str | None = None,
    trend_type: str | None = None,
    sort: str = "strength",
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[dict], int]:
    where, params = _build_where(run_id=run_id, subject=subject, theme=theme, trend_type=trend_type)
    order = _SORT_MAP.get(sort, _SORT_MAP["strength"])

    with get_conn() as conn:
        total = conn.execute(f"SELECT count(*) as c FROM trend_signals {where}", params).fetchone()["c"]  # noqa: S608
        rows = conn.execute(
            f"SELECT run_id, trend_id, theme, trend_json, created_at FROM trend_signals {where} ORDER BY {order} LIMIT ? OFFSET ?",  # noqa: S608
            (*params, page_size, (page - 1) * page_size),
        ).fetchall()
    return [_to_summary(r) for r in rows], total


def get_trend(trend_id: str, run_id: str | None = None) -> dict | None:
    where = "WHERE trend_id = ?"
    params: list = [trend_id]
    if run_id:
        where += " AND run_id = ?"
        params.append(run_id)
    with get_conn() as conn:
        row = conn.execute(
            f"SELECT run_id, trend_id, theme, trend_json, created_at FROM trend_signals {where} LIMIT 1",  # noqa: S608
            params,
        ).fetchone()
    if not row:
        return None
    return _to_detail(row)


def _to_summary(row: dict) -> dict:
    data = json.loads(row["trend_json"])
    return {
        "trend_id": row["trend_id"],
        "subject": data.get("subject"),
        "theme": data.get("theme") or row.get("theme"),
        "trend_type": data.get("trend_type"),
        "direction": data.get("direction"),
        "strength_score": data.get("strength_score", 0),
        "novelty_score": data.get("novelty_score", 0),
        "corroboration_score": data.get("corroboration_score", 0),
        "confidence": data.get("confidence", 0),
        "why_it_matters": data.get("why_it_matters"),
        "event_count": len(data.get("event_ids", [])),
        "run_id": row["run_id"],
        "created_at": row["created_at"],
    }


def _to_detail(row: dict) -> dict:
    data = json.loads(row["trend_json"])
    summary = _to_summary(row)
    summary.update({
        "window": data.get("window"),
        "event_ids": data.get("event_ids", []),
        "bundle_ids": data.get("bundle_ids", []),
        "metadata": data.get("metadata", {}),
    })
    return summary


def _build_where(
    *,
    run_id: str | None = None,
    subject: str | None = None,
    theme: str | None = None,
    trend_type: str | None = None,
) -> tuple[str, list]:
    clauses: list[str] = []
    params: list = []
    if run_id:
        clauses.append("run_id = ?")
        params.append(run_id)
    if subject:
        clauses.append("json_extract(trend_json, '$.subject') = ?")
        params.append(subject)
    if theme:
        clauses.append("(theme = ? OR json_extract(trend_json, '$.theme') = ?)")
        params.extend([theme, theme])
    if trend_type:
        clauses.append("json_extract(trend_json, '$.trend_type') = ?")
        params.append(trend_type)
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    return where, params
