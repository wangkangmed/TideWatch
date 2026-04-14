"""Decision support layer node."""

from __future__ import annotations

from tide_watch.models.graph_state import TideWatchState


def run_decision_support(state: TideWatchState) -> dict[str, object]:
    signals = []
    recs = []
    findings = state.get("findings") or []
    for idx, finding in enumerate(findings):
        signal_id = f"ds_{idx+1}"
        signals.append(
            {
                "signal_id": signal_id,
                "finding_id": finding.get("finding_id"),
                "signal_type": "watch",
                "decision_relevance_score": finding.get("decision_relevance_score", 0.5),
                "supporting_finding_ids": [finding.get("finding_id")],
                "supporting_event_ids": list(finding.get("supporting_event_ids") or []),
                "supporting_evidence_ids": list(finding.get("supporting_evidence_ids") or []),
            }
        )
        recs.append(
            {
                "recommendation_id": f"rec_{idx+1}",
                "signal_id": signal_id,
                "recommended_action": "increase_monitoring",
                "priority": finding.get("decision_relevance_score", 0.5),
                "supporting_finding_ids": [finding.get("finding_id")],
                "supporting_event_ids": list(finding.get("supporting_event_ids") or []),
                "supporting_evidence_ids": list(finding.get("supporting_evidence_ids") or []),
            }
        )
    briefs = []
    if signals:
        briefs.append(
            {
                "brief_id": "dbrief_1",
                "brief_type": "watch_brief",
                "title": "Decision watch brief",
                "key_signals": [s["signal_id"] for s in signals[:3]],
                "recommendations": [r["recommendation_id"] for r in recs[:3]],
            }
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
