"""Overview / dashboard aggregation queries."""

from __future__ import annotations

from .db import get_conn


def get_overview_counts(run_id: str) -> dict:
    with get_conn() as conn:
        def _c(table: str) -> int:
            return conn.execute(f"SELECT count(*) as c FROM {table} WHERE run_id = ?", (run_id,)).fetchone()["c"]  # noqa: S608

        return {
            "documents": _c("documents"),
            "evidence": _c("evidence_items"),
            "events": _c("events"),
            "trends": _c("trend_signals"),
            "findings": _c("intelligence_findings"),
            "recommendations": _c("recommendation_items"),
            "briefs": _c("decision_briefs"),
            "alerts": _c("alert_items"),
        }
