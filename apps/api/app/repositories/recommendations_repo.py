"""Recommendation queries."""

from __future__ import annotations

import json

from .db import get_conn


def list_recommendations(
    *,
    run_id: str | None = None,
    recommended_action: str | None = None,
    sort: str = "priority",
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[dict], int]:
    where, params = _build_where(run_id=run_id, recommended_action=recommended_action)
    sort_col = {
        "priority": "json_extract(rec_json, '$.priority') DESC",
        "created_at": "created_at DESC",
    }.get(sort, "json_extract(rec_json, '$.priority') DESC")

    with get_conn() as conn:
        total = conn.execute(f"SELECT count(*) as c FROM recommendation_items {where}", params).fetchone()["c"]  # noqa: S608
        rows = conn.execute(
            f"SELECT run_id, recommendation_id, signal_id, recommended_action, rec_json, created_at "
            f"FROM recommendation_items {where} ORDER BY {sort_col} LIMIT ? OFFSET ?",  # noqa: S608
            (*params, page_size, (page - 1) * page_size),
        ).fetchall()
    return [_to_summary(r) for r in rows], total


def get_recommendation(recommendation_id: str, run_id: str | None = None) -> dict | None:
    where = "WHERE recommendation_id = ?"
    params: list = [recommendation_id]
    if run_id:
        where += " AND run_id = ?"
        params.append(run_id)

    with get_conn() as conn:
        row = conn.execute(
            f"SELECT run_id, recommendation_id, signal_id, recommended_action, rec_json, created_at "
            f"FROM recommendation_items {where} LIMIT 1",  # noqa: S608
            params,
        ).fetchone()
    if not row:
        return None

    data = json.loads(row["rec_json"])
    detail = _to_summary(row)
    detail.update({
        "supporting_finding_ids": data.get("supporting_finding_ids", []),
        "supporting_event_ids": data.get("supporting_event_ids", []),
        "supporting_evidence_ids": data.get("supporting_evidence_ids", []),
        "metadata": data.get("metadata", {}),
    })

    run = row["run_id"]
    with get_conn() as conn:
        sig_id = row["signal_id"]
        if sig_id:
            sig_row = conn.execute(
                "SELECT signal_json FROM decision_signals WHERE signal_id = ? AND run_id = ?",
                (sig_id, run),
            ).fetchone()
            if sig_row:
                detail["related_signal"] = json.loads(sig_row["signal_json"])

        detail["related_findings"] = []
        for fid in detail["supporting_finding_ids"][:10]:
            frow = conn.execute(
                "SELECT finding_json FROM intelligence_findings WHERE finding_id = ? AND run_id = ?",
                (fid, run),
            ).fetchone()
            if frow:
                detail["related_findings"].append(json.loads(frow["finding_json"]))

    return detail


def _to_summary(row: dict) -> dict:
    data = json.loads(row["rec_json"])
    return {
        "recommendation_id": row["recommendation_id"],
        "signal_id": row.get("signal_id"),
        "recommended_action": data.get("recommended_action") or row.get("recommended_action"),
        "priority": data.get("priority", 0),
        "rationale": data.get("rationale"),
        "why_now": data.get("why_now"),
        "requires_human_review": data.get("requires_human_review", False),
        "finding_count": len(data.get("supporting_finding_ids", [])),
        "event_count": len(data.get("supporting_event_ids", [])),
        "evidence_count": len(data.get("supporting_evidence_ids", [])),
        "run_id": row["run_id"],
        "created_at": row["created_at"],
    }


def _build_where(
    *,
    run_id: str | None = None,
    recommended_action: str | None = None,
) -> tuple[str, list]:
    clauses: list[str] = []
    params: list = []
    if run_id:
        clauses.append("run_id = ?")
        params.append(run_id)
    if recommended_action:
        clauses.append("(recommended_action = ? OR json_extract(rec_json, '$.recommended_action') = ?)")
        params.extend([recommended_action, recommended_action])
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    return where, params
