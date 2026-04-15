"""Watchlist queries."""

from __future__ import annotations

import json

from .db import get_conn


def list_watchlists(
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
        if not _table_exists(conn, "watchlists"):
            return [], 0
        total = conn.execute(f"SELECT count(*) as c FROM watchlists {w}", params).fetchone()["c"]  # noqa: S608
        rows = conn.execute(
            f"SELECT run_id, watchlist_id, watchlist_json, created_at FROM watchlists {w} ORDER BY created_at DESC LIMIT ? OFFSET ?",  # noqa: S608
            (*params, page_size, (page - 1) * page_size),
        ).fetchall()

    result = []
    for r in rows:
        data = json.loads(r["watchlist_json"])
        entity_count = len(data.get("entities", []))
        topic_count = len(data.get("topics", []))
        result.append({
            "watchlist_id": r["watchlist_id"],
            "entity_count": entity_count,
            "topic_count": topic_count,
            "run_id": r["run_id"],
            "created_at": r["created_at"],
        })
    return result, total


def get_watchlist(watchlist_id: str, run_id: str | None = None) -> dict | None:
    where = "WHERE watchlist_id = ?"
    params: list = [watchlist_id]
    if run_id:
        where += " AND run_id = ?"
        params.append(run_id)

    with get_conn() as conn:
        if not _table_exists(conn, "watchlists"):
            return None
        row = conn.execute(
            f"SELECT run_id, watchlist_id, watchlist_json, created_at FROM watchlists {where} LIMIT 1",  # noqa: S608
            params,
        ).fetchone()
    if not row:
        return None

    data = json.loads(row["watchlist_json"])
    run = row["run_id"]

    entities = []
    with get_conn() as conn:
        if _table_exists(conn, "watchlist_entities"):
            erows = conn.execute(
                "SELECT canonical_name, entity_type, weight, aliases_json FROM watchlist_entities "
                "WHERE watchlist_id = ? AND run_id = ?",
                (watchlist_id, run),
            ).fetchall()
            for er in erows:
                aliases = []
                try:
                    aliases = json.loads(er["aliases_json"])
                except Exception:
                    pass
                entities.append({
                    "canonical_name": er["canonical_name"],
                    "entity_type": er.get("entity_type"),
                    "weight": er.get("weight", 1.0),
                    "aliases": aliases,
                })

    topics = []
    with get_conn() as conn:
        if _table_exists(conn, "watchlist_topics"):
            trows = conn.execute(
                "SELECT topic_name, weight, keywords_json FROM watchlist_topics "
                "WHERE watchlist_id = ? AND run_id = ?",
                (watchlist_id, run),
            ).fetchall()
            for tr in trows:
                keywords = []
                try:
                    keywords = json.loads(tr["keywords_json"])
                except Exception:
                    pass
                topics.append({
                    "topic_name": tr["topic_name"],
                    "weight": tr.get("weight", 1.0),
                    "keywords": keywords,
                })

    if not entities:
        entities = [
            {
                "canonical_name": e.get("canonical_name", ""),
                "entity_type": e.get("entity_type"),
                "weight": e.get("weight", 1.0),
                "aliases": e.get("aliases", []),
            }
            for e in data.get("entities", [])
        ]
    if not topics:
        topics = [
            {
                "topic_name": t.get("topic_name", t.get("name", "")),
                "weight": t.get("weight", 1.0),
                "keywords": t.get("keywords", []),
            }
            for t in data.get("topics", [])
        ]

    return {
        "watchlist_id": row["watchlist_id"],
        "entity_count": len(entities),
        "topic_count": len(topics),
        "entities": entities,
        "topics": topics,
        "metadata": data.get("metadata", {}),
        "run_id": run,
        "created_at": row["created_at"],
    }


def _table_exists(conn, table: str) -> bool:
    row = conn.execute(
        "SELECT count(*) as c FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone()
    return row["c"] > 0
