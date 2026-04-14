"""Intelligence layer node: events -> trends/findings/outputs."""

from __future__ import annotations

from typing import Any

from tide_watch.models.graph_state import TideWatchState
from tide_watch.models.pipeline import (
    AlertItem,
    BriefingItem,
    EventItem,
    Finding,
    TrendSignal,
)


def _evt_field(evt: EventItem | dict, field: str, default: Any = None) -> Any:
    if isinstance(evt, dict):
        return evt.get(field, default)
    return getattr(evt, field, default)


def run_intelligence(state: TideWatchState) -> dict[str, object]:
    events = state.get("events") or []
    trends: list[TrendSignal] = []
    findings: list[Finding] = []
    alerts: list[AlertItem] = []
    briefs: list[BriefingItem] = []

    n_events = len(events)
    for idx, event in enumerate(events):
        trend_id = f"tr_{idx+1}"
        finding_id = f"fd_{idx+1}"
        event_id = _evt_field(event, "event_id", "")
        event_title = _evt_field(event, "title", "")
        supporting_evi = list(_evt_field(event, "supporting_evidence_ids") or [])

        source_count = 1
        strength = min(1.0, 0.3 + 0.1 * source_count)
        corroboration = min(1.0, 0.4 + 0.05 * source_count)
        importance = min(1.0, 0.3 + (0.7 * (1 - idx / max(n_events, 1))))
        relevance = importance * 0.9

        trends.append(
            TrendSignal(
                trend_id=trend_id,
                title=event_title,
                strength_score=round(strength, 3),
                corroboration_score=round(corroboration, 3),
                supporting_event_ids=[event_id],
            )
        )
        findings.append(
            Finding(
                finding_id=finding_id,
                trend_id=trend_id,
                finding_type="watch_signal",
                importance_score=round(importance, 3),
                decision_relevance_score=round(relevance, 3),
                supporting_event_ids=[event_id],
                supporting_evidence_ids=supporting_evi,
            )
        )

    sorted_findings = sorted(findings, key=lambda f: f.importance_score, reverse=True)
    for rank, f in enumerate(sorted_findings):
        if f.importance_score >= 0.7 or rank == 0:
            level = "high" if f.importance_score >= 0.8 else "medium"
            alerts.append(AlertItem(alert_id=f"al_{rank+1}", finding_id=f.finding_id, level=level))
        if rank < 3:
            briefs.append(BriefingItem(
                briefing_id=f"br_{rank+1}",
                finding_id=f.finding_id,
                title=f"Watch item #{rank+1}",
            ))

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
