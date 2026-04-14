"""Event queries."""

from __future__ import annotations

import json

from .db import get_conn


def list_events(
    *,
    run_id: str | None = None,
    event_type: str | None = None,
    sort: str = "significance",
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[dict], int]:
    where, params = _build_where(run_id=run_id, event_type=event_type)
    sort_col = {
        "significance": "json_extract(event_json, '$.significance_score') DESC",
        "created_at": "created_at DESC",
    }.get(sort, "json_extract(event_json, '$.significance_score') DESC")

    with get_conn() as conn:
        total = conn.execute(f"SELECT count(*) as c FROM events {where}", params).fetchone()["c"]  # noqa: S608
        rows = conn.execute(
            f"SELECT run_id, event_id, event_json, created_at FROM events {where} ORDER BY {sort_col} LIMIT ? OFFSET ?",  # noqa: S608
            (*params, page_size, (page - 1) * page_size),
        ).fetchall()
    return [_to_summary(r) for r in rows], total


def get_event(event_id: str, run_id: str | None = None) -> dict | None:
    where = "WHERE event_id = ?"
    params: list = [event_id]
    if run_id:
        where += " AND run_id = ?"
        params.append(run_id)

    with get_conn() as conn:
        row = conn.execute(
            f"SELECT run_id, event_id, event_json, created_at FROM events {where} LIMIT 1",  # noqa: S608
            params,
        ).fetchone()
    if not row:
        return None

    data = json.loads(row["event_json"])
    run = row["run_id"]

    with get_conn() as conn:
        evi_ids = data.get("supporting_evidence_ids", [])
        evidence_items = []
        for evid in evi_ids[:20]:
            evrow = conn.execute(
                "SELECT item_json FROM evidence_items WHERE evidence_id = ? AND run_id = ?",
                (evid, run),
            ).fetchone()
            if evrow:
                evidence_items.append(json.loads(evrow["item_json"]))

        links = conn.execute(
            "SELECT link_json FROM event_evidence_links WHERE event_id = ? AND run_id = ?",
            (event_id, run),
        ).fetchall()
        if not evi_ids and links:
            for lk in links:
                ld = json.loads(lk["link_json"])
                evid = ld.get("evidence_id")
                if evid:
                    evrow = conn.execute(
                        "SELECT item_json FROM evidence_items WHERE evidence_id = ? AND run_id = ?",
                        (evid, run),
                    ).fetchone()
                    if evrow:
                        evidence_items.append(json.loads(evrow["item_json"]))

    summary = _to_summary(row)
    summary.update({
        "object": data.get("object"),
        "event_time": data.get("event_time"),
        "time_precision": data.get("time_precision"),
        "status": data.get("status"),
        "supporting_evidence_ids": data.get("supporting_evidence_ids", []),
        "entities": data.get("entities", {}),
        "metadata": data.get("metadata", {}),
        "evidence_items": evidence_items,
    })
    return summary


def _to_summary(row: dict) -> dict:
    data = json.loads(row["event_json"])
    return {
        "event_id": row["event_id"],
        "event_type": data.get("event_type"),
        "subject": data.get("subject"),
        "canonical_title": data.get("canonical_title") or data.get("title"),
        "significance_score": data.get("significance_score", 0),
        "confidence": data.get("confidence", 0),
        "evidence_count": len(data.get("supporting_evidence_ids", [])),
        "run_id": row["run_id"],
        "created_at": row["created_at"],
    }


def _build_where(
    *,
    run_id: str | None = None,
    event_type: str | None = None,
) -> tuple[str, list]:
    clauses: list[str] = []
    params: list = []
    if run_id:
        clauses.append("run_id = ?")
        params.append(run_id)
    if event_type:
        clauses.append("json_extract(event_json, '$.event_type') = ?")
        params.append(event_type)
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    return where, params
