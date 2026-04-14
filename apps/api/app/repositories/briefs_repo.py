"""Brief and briefing-item queries."""

from __future__ import annotations

import json

from .db import get_conn


def list_briefs(
    *,
    run_id: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[dict], int]:
    where, params = [], []
    if run_id:
        where.append("run_id = ?")
        params.append(run_id)
    w = ("WHERE " + " AND ".join(where)) if where else ""

    with get_conn() as conn:
        total = conn.execute(f"SELECT count(*) as c FROM decision_briefs {w}", params).fetchone()["c"]  # noqa: S608
        rows = conn.execute(
            f"SELECT run_id, brief_id, brief_type, brief_json, created_at FROM decision_briefs {w} ORDER BY created_at DESC LIMIT ? OFFSET ?",  # noqa: S608
            (*params, page_size, (page - 1) * page_size),
        ).fetchall()
    return [_to_summary(r) for r in rows], total


def get_brief(brief_id: str, run_id: str | None = None) -> dict | None:
    where = "WHERE brief_id = ?"
    params: list = [brief_id]
    if run_id:
        where += " AND run_id = ?"
        params.append(run_id)

    with get_conn() as conn:
        row = conn.execute(
            f"SELECT run_id, brief_id, brief_type, brief_json, created_at FROM decision_briefs {where} LIMIT 1",  # noqa: S608
            params,
        ).fetchone()
    if not row:
        return None

    data = json.loads(row["brief_json"])
    return {
        **_to_summary(row),
        "key_signals": data.get("key_signals", []),
        "recommendations": data.get("recommendations", []),
        "top_risks": data.get("top_risks", []),
        "top_opportunities": data.get("top_opportunities", []),
        "top_watch_items": data.get("top_watch_items", []),
        "supporting_finding_ids": data.get("supporting_finding_ids", []),
        "supporting_event_ids": data.get("supporting_event_ids", []),
        "supporting_evidence_ids": data.get("supporting_evidence_ids", []),
        "metadata": data.get("metadata", {}),
    }


def list_briefing_items(
    *,
    run_id: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[dict], int]:
    where, params = [], []
    if run_id:
        where.append("run_id = ?")
        params.append(run_id)
    w = ("WHERE " + " AND ".join(where)) if where else ""

    with get_conn() as conn:
        total = conn.execute(f"SELECT count(*) as c FROM briefing_items {w}", params).fetchone()["c"]  # noqa: S608
        rows = conn.execute(
            f"SELECT run_id, briefing_item_id, briefing_json, created_at FROM briefing_items {w} ORDER BY created_at DESC LIMIT ? OFFSET ?",  # noqa: S608
            (*params, page_size, (page - 1) * page_size),
        ).fetchall()

    result = []
    for r in rows:
        data = json.loads(r["briefing_json"])
        result.append({
            "briefing_item_id": data.get("briefing_item_id") or r["briefing_item_id"],
            "title": data.get("title"),
            "summary": data.get("summary"),
            "theme": data.get("theme"),
            "importance_score": data.get("importance_score", 0),
            "decision_relevance": data.get("decision_relevance", 0),
            "evidence_count": data.get("evidence_count", 0),
            "run_id": r["run_id"],
            "created_at": r["created_at"],
        })
    return result, total


def _to_summary(row: dict) -> dict:
    data = json.loads(row["brief_json"])
    return {
        "brief_id": row["brief_id"],
        "brief_type": data.get("brief_type") or row.get("brief_type"),
        "title": data.get("title"),
        "summary": data.get("summary"),
        "signal_count": len(data.get("key_signals", [])),
        "recommendation_count": len(data.get("recommendations", [])),
        "run_id": row["run_id"],
        "created_at": row["created_at"],
    }
