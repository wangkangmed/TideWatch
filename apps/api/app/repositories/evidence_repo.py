"""Evidence queries."""

from __future__ import annotations

import json

from .db import get_conn


def get_evidence(evidence_id: str, run_id: str | None = None) -> dict | None:
    where = "WHERE evidence_id = ?"
    params: list = [evidence_id]
    if run_id:
        where += " AND run_id = ?"
        params.append(run_id)

    with get_conn() as conn:
        row = conn.execute(
            f"SELECT run_id, evidence_id, document_id, item_json, source_trace_json, created_at "
            f"FROM evidence_items {where} LIMIT 1",  # noqa: S608
            params,
        ).fetchone()
    if not row:
        return None

    data = json.loads(row["item_json"])
    run = row["run_id"]
    doc_data = None

    doc_info = data.get("document", {})
    if not doc_info:
        doc_id = row.get("document_id") or data.get("doc_id")
        if doc_id:
            with get_conn() as conn:
                doc_row = conn.execute(
                    "SELECT doc_json FROM documents WHERE document_id = ? AND run_id = ?",
                    (doc_id, run),
                ).fetchone()
                if doc_row:
                    doc_data = json.loads(doc_row["doc_json"])
    else:
        doc_data = doc_info

    with get_conn() as conn:
        links = conn.execute(
            "SELECT event_id FROM event_evidence_links WHERE evidence_id = ? AND run_id = ?",
            (evidence_id, run),
        ).fetchall()
        linked_events = []
        for lk in links:
            erow = conn.execute(
                "SELECT event_json FROM events WHERE event_id = ? AND run_id = ?",
                (lk["event_id"], run),
            ).fetchone()
            if erow:
                linked_events.append(json.loads(erow["event_json"]))

    trace = {}
    if row.get("source_trace_json"):
        try:
            trace = json.loads(row["source_trace_json"])
        except Exception:
            pass

    return {
        "evidence_id": evidence_id,
        "document_id": doc_data.get("doc_id") if doc_data else row.get("document_id"),
        "source_id": data.get("source_id") or (doc_data or {}).get("source_id"),
        "origin_type": (doc_data or {}).get("origin_type"),
        "title": (doc_data or {}).get("title"),
        "canonical_url": (doc_data or {}).get("canonical_url"),
        "body_text": data.get("text") or (doc_data or {}).get("body_text"),
        "source_trace": trace,
        "document": doc_data,
        "linked_events": linked_events,
        "run_id": run,
        "created_at": row["created_at"],
    }
