"""Intelligence layer node: events -> trends/findings/outputs."""

from __future__ import annotations

from tide_watch.models.graph_state import TideWatchState


def run_intelligence(state: TideWatchState) -> dict[str, object]:
    events = state.get("events") or []
    trends = []
    findings = []
    alerts = []
    briefs = []
    for idx, event in enumerate(events):
        trend_id = f"tr_{idx+1}"
        finding_id = f"fd_{idx+1}"
        trends.append(
            {
                "trend_id": trend_id,
                "title": event.get("title"),
                "strength_score": 0.5,
                "corroboration_score": 0.6,
                "supporting_event_ids": [event.get("event_id")],
            }
        )
        findings.append(
            {
                "finding_id": finding_id,
                "trend_id": trend_id,
                "finding_type": "watch_signal",
                "importance_score": 0.5,
                "decision_relevance_score": 0.5,
                "supporting_event_ids": [event.get("event_id")],
                "supporting_evidence_ids": list(event.get("supporting_evidence_ids") or []),
            }
        )
    if findings:
        alerts.append({"alert_id": "al_1", "finding_id": findings[0]["finding_id"], "level": "medium"})
        briefs.append({"briefing_id": "br_1", "finding_id": findings[0]["finding_id"], "title": "Top watch item"})
    return {
        "trends": trends,
        "findings": findings,
        "alerts": alerts,
        "briefing_items": briefs,
        "intelligence_metadata": {
            "trends": len(trends),
            "findings": len(findings),
            "alerts": len(alerts),
            "briefing_items": len(briefs),
        },
    }
