"""Finding queries."""

from __future__ import annotations

import json

from .db import get_conn


def list_findings(
    *,
    run_id: str | None = None,
    finding_type: str | None = None,
    min_importance: float | None = None,
    min_decision_relevance: float | None = None,
    sort: str = "importance",
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[dict], int]:
    where, params = _build_where(
        run_id=run_id,
        finding_type=finding_type,
        min_importance=min_importance,
        min_decision_relevance=min_decision_relevance,
    )
    sort_col = {
        "importance": "json_extract(finding_json, '$.importance_score') DESC",
        "decision_relevance": "json_extract(finding_json, '$.decision_relevance_score') DESC",
        "created_at": "created_at DESC",
    }.get(sort, "json_extract(finding_json, '$.importance_score') DESC")

    with get_conn() as conn:
        total = conn.execute(f"SELECT count(*) as c FROM intelligence_findings {where}", params).fetchone()["c"]  # noqa: S608
        rows = conn.execute(
            f"SELECT run_id, finding_id, finding_type, finding_json, created_at FROM intelligence_findings {where} ORDER BY {sort_col} LIMIT ? OFFSET ?",  # noqa: S608
            (*params, page_size, (page - 1) * page_size),
        ).fetchall()
    return [_to_summary(r) for r in rows], total


def get_finding(finding_id: str, run_id: str | None = None) -> dict | None:
    where = "WHERE finding_id = ?"
    params: list = [finding_id]
    if run_id:
        where += " AND run_id = ?"
        params.append(run_id)

    with get_conn() as conn:
        row = conn.execute(
            f"SELECT run_id, finding_id, finding_type, finding_json, created_at FROM intelligence_findings {where} LIMIT 1",  # noqa: S608
            params,
        ).fetchone()
    if not row:
        return None

    data = json.loads(row["finding_json"])
    detail = _to_summary(row)
    detail.update({
        "trend_id": data.get("metadata", {}).get("trend_id") or data.get("trend_id"),
        "supporting_event_ids": data.get("supporting_event_ids", []),
        "supporting_evidence_ids": data.get("supporting_evidence_ids", []),
        "explain": data.get("metadata", {}).get("explain", []),
        "topic_hits": data.get("metadata", {}).get("topic_hits", []),
        "metadata": data.get("metadata", {}),
    })

    run = row["run_id"]
    with get_conn() as conn:
        trend_id = detail.get("trend_id")
        if trend_id:
            trend_row = conn.execute(
                "SELECT trend_json FROM trend_signals WHERE trend_id = ? AND run_id = ?",
                (trend_id, run),
            ).fetchone()
            if trend_row:
                detail["related_trend"] = json.loads(trend_row["trend_json"])

        detail["related_events"] = []
        for eid in detail["supporting_event_ids"][:10]:
            erow = conn.execute(
                "SELECT event_json FROM events WHERE event_id = ? AND run_id = ?",
                (eid, run),
            ).fetchone()
            if erow:
                event_data = json.loads(erow["event_json"])
                detail["related_events"].append({
                    "event_id": event_data.get("event_id", eid),
                    "canonical_title": event_data.get("canonical_title") or event_data.get("title") or eid,
                    "event_type": event_data.get("event_type"),
                    "subject": event_data.get("subject"),
                    "significance_score": event_data.get("significance_score", 0),
                    "confidence": event_data.get("confidence", 0),
                })

        detail["related_evidence"] = []
        for evid in detail["supporting_evidence_ids"][:10]:
            evrow = conn.execute(
                "SELECT document_id, item_json, source_trace_json FROM evidence_items WHERE evidence_id = ? AND run_id = ?",
                (evid, run),
            ).fetchone()
            if evrow:
                evidence_data = json.loads(evrow["item_json"])
                document = None
                doc_id = evrow.get("document_id") or evidence_data.get("doc_id")
                if doc_id:
                    doc_row = conn.execute(
                        "SELECT doc_json FROM documents WHERE document_id = ? AND run_id = ?",
                        (doc_id, run),
                    ).fetchone()
                    if doc_row:
                        document = json.loads(doc_row["doc_json"])
                detail["related_evidence"].append({
                    "evidence_id": evidence_data.get("evidence_id", evid),
                    "source_id": evidence_data.get("source_id") or (document or {}).get("source_id"),
                    "title": (document or {}).get("title"),
                    "canonical_url": (document or {}).get("canonical_url"),
                    "document": {
                        "title": (document or {}).get("title"),
                        "canonical_url": (document or {}).get("canonical_url"),
                        "source_id": (document or {}).get("source_id"),
                    },
                    "snippet": (evidence_data.get("text") or "")[:240],
                    "source_trace": json.loads(evrow["source_trace_json"]) if evrow.get("source_trace_json") else {},
                })

        recs = conn.execute(
            "SELECT rec_json FROM recommendation_items r "
            "JOIN decision_signals s ON r.signal_id = s.signal_id AND r.run_id = s.run_id "
            "WHERE s.finding_id = ? AND s.run_id = ?",
            (finding_id, run),
        ).fetchall()
        detail["related_recommendations"] = [json.loads(r["rec_json"]) for r in recs]

    return detail


def _to_summary(row: dict) -> dict:
    data = json.loads(row["finding_json"])
    metadata = data.get("metadata", {}) or {}
    title = data.get("display_title") or data.get("title") or row["finding_id"]
    return {
        "finding_id": row["finding_id"],
        "subject": data.get("subject"),
        "theme": data.get("theme"),
        "finding_type": data.get("finding_type") or row.get("finding_type"),
        "title": title,
        "display_title": title,
        "summary": data.get("summary"),
        "confidence": data.get("confidence", 0),
        "importance_score": data.get("importance_score", 0),
        "decision_relevance_score": data.get("decision_relevance_score", 0),
        "why_it_matters": data.get("why_it_matters"),
        "recommended_actions": data.get("recommended_actions", []),
        "watchlist_hits": metadata.get("watchlist_hits", []),
        "topic_hits": metadata.get("topic_hits", []),
        "explain": metadata.get("explain", []),
        "event_count": len(data.get("supporting_event_ids", [])),
        "evidence_count": len(data.get("supporting_evidence_ids", [])),
        "run_id": row["run_id"],
        "created_at": row["created_at"],
    }


def _build_where(
    *,
    run_id: str | None = None,
    finding_type: str | None = None,
    min_importance: float | None = None,
    min_decision_relevance: float | None = None,
) -> tuple[str, list]:
    clauses: list[str] = []
    params: list = []
    if run_id:
        clauses.append("run_id = ?")
        params.append(run_id)
    if finding_type:
        clauses.append("(finding_type = ? OR json_extract(finding_json, '$.finding_type') = ?)")
        params.extend([finding_type, finding_type])
    if min_importance is not None:
        clauses.append("json_extract(finding_json, '$.importance_score') >= ?")
        params.append(min_importance)
    if min_decision_relevance is not None:
        clauses.append("json_extract(finding_json, '$.decision_relevance_score') >= ?")
        params.append(min_decision_relevance)
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    return where, params
