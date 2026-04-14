"""Decision support layer node."""

from __future__ import annotations

from typing import Any

from tide_watch.models.graph_state import TideWatchState
from tide_watch.models.pipeline import (
    DecisionBrief,
    DecisionSignal,
    Finding,
    RecommendationItem,
)


def _find_field(finding: Finding | dict, field: str, default: Any = None) -> Any:
    if isinstance(finding, dict):
        return finding.get(field, default)
    return getattr(finding, field, default)


def run_decision_support(state: TideWatchState) -> dict[str, object]:
    signals: list[DecisionSignal] = []
    recs: list[RecommendationItem] = []
    findings = state.get("findings") or []

    for idx, finding in enumerate(findings):
        signal_id = f"ds_{idx+1}"
        finding_id = _find_field(finding, "finding_id", "")
        relevance = _find_field(finding, "decision_relevance_score", 0.5)
        evt_ids = list(_find_field(finding, "supporting_event_ids") or [])
        evi_ids = list(_find_field(finding, "supporting_evidence_ids") or [])

        signals.append(
            DecisionSignal(
                signal_id=signal_id,
                finding_id=finding_id,
                signal_type="watch",
                decision_relevance_score=relevance,
                supporting_finding_ids=[finding_id],
                supporting_event_ids=evt_ids,
                supporting_evidence_ids=evi_ids,
            )
        )
        recs.append(
            RecommendationItem(
                recommendation_id=f"rec_{idx+1}",
                signal_id=signal_id,
                recommended_action="increase_monitoring",
                priority=relevance,
                supporting_finding_ids=[finding_id],
                supporting_event_ids=evt_ids,
                supporting_evidence_ids=evi_ids,
            )
        )

    briefs: list[DecisionBrief] = []
    if signals:
        briefs.append(
            DecisionBrief(
                brief_id="dbrief_1",
                brief_type="watch_brief",
                title="Decision watch brief",
                key_signals=[s.signal_id for s in signals[:3]],
                recommendations=[r.recommendation_id for r in recs[:3]],
            )
        )
    return {
        "decision_signals": signals,
        "recommendation_items": recs,
        "decision_briefs": briefs,
        "decision_support_metadata": {
            "signals": len(signals),
            "recommendations": len(recs),
            "briefs": len(briefs),
        },
    }
