"""GET /api/v1/overview – dashboard snapshot."""

from __future__ import annotations

from fastapi import APIRouter, Query

from ..repositories import (
    alerts_repo,
    briefs_repo,
    findings_repo,
    overview_repo,
    recommendations_repo,
    runs_repo,
    trends_repo,
)
from ..schemas.common import paginate

router = APIRouter()


@router.get("/overview")
def overview(run_id: str | None = Query(None)):
    rid = run_id or runs_repo.get_latest_run_id()
    if not rid:
        return {"counts": {}, "latest_run": None, "top_trends": [], "top_findings": [], "top_recommendations": [], "recent_alerts": [], "latest_briefs": []}

    counts = overview_repo.get_overview_counts(rid)
    latest_run = runs_repo.get_run(rid)
    top_trends, _ = trends_repo.list_trends(run_id=rid, sort="strength", page=1, page_size=5)
    top_findings, _ = findings_repo.list_findings(run_id=rid, sort="importance", page=1, page_size=5)
    top_recs, _ = recommendations_repo.list_recommendations(run_id=rid, sort="priority", page=1, page_size=5)
    alerts, _ = alerts_repo.list_alerts(run_id=rid, page=1, page_size=5)
    briefs, _ = briefs_repo.list_briefs(run_id=rid, page=1, page_size=3)

    return {
        "counts": counts,
        "latest_run": latest_run,
        "top_trends": top_trends,
        "top_findings": top_findings,
        "top_recommendations": top_recs,
        "recent_alerts": alerts,
        "latest_briefs": briefs,
    }
