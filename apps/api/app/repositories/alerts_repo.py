"""Alert queries."""

from __future__ import annotations

import json

from .db import get_conn


def list_alerts(
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
        total = conn.execute(f"SELECT count(*) as c FROM alert_items {w}", params).fetchone()["c"]  # noqa: S608
        rows = conn.execute(
            f"SELECT run_id, alert_id, alert_json, created_at FROM alert_items {w} ORDER BY created_at DESC LIMIT ? OFFSET ?",  # noqa: S608
            (*params, page_size, (page - 1) * page_size),
        ).fetchall()

    result = []
    for r in rows:
        data = json.loads(r["alert_json"])
        finding_id = data.get("finding_id")

        finding_data = {}
        if finding_id:
            frow = conn.execute(
                "SELECT finding_json FROM intelligence_findings WHERE finding_id = ? AND run_id = ?",
                (finding_id, r["run_id"]),
            ).fetchone()
            if frow:
                finding_data = json.loads(frow["finding_json"])

        result.append({
            "alert_id": r["alert_id"],
            "level": data.get("level"),
            "finding_id": finding_id,
            "signal_type": data.get("signal_type"),
            "title": finding_data.get("title") or data.get("title"),
            "summary": finding_data.get("summary") or data.get("summary"),
            "importance_score": finding_data.get("importance_score", 0),
            "run_id": r["run_id"],
            "created_at": r["created_at"],
        })
    return result, total
