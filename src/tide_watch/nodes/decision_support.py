"""Decision support layer node with recommendation consolidation and narrative briefs."""

from __future__ import annotations

import hashlib
from collections import defaultdict
from typing import Any

from tide_watch.models.graph_state import TideWatchState
from tide_watch.models.pipeline import (
    DecisionBrief,
    DecisionSignal,
    Finding,
    RecommendationItem,
)

_ACTION_CONFIG: dict[str, dict[str, Any]] = {
    "risk_signal": {
        "action": "escalate_risk_review",
        "display": "Escalate risk review",
        "bucket": "risk",
        "boost": 0.18,
        "rationale": "Several risk-oriented findings indicate a concrete downside that should be reviewed quickly.",
        "why_now": "Risk indicators are already material and can affect stakeholder decisions.",
    },
    "opportunity_signal": {
        "action": "pursue_opportunity_validation",
        "display": "Validate opportunity",
        "bucket": "opportunity",
        "boost": 0.16,
        "rationale": "Multiple opportunity-oriented findings suggest a concrete opening worth validating.",
        "why_now": "Fresh opportunity cues are present and may be time-sensitive.",
    },
    "competition_signal": {
        "action": "track_competitor_response",
        "display": "Track competitor response",
        "bucket": "competition",
        "boost": 0.12,
        "rationale": "Competitive findings point to a peer move that should be tracked as one combined response thread.",
        "why_now": "Peer signals are active enough to justify a consolidated watch item.",
    },
    "adoption_signal": {
        "action": "track_adoption_signals",
        "display": "Track adoption signals",
        "bucket": "adoption",
        "boost": 0.14,
        "rationale": "Adoption-oriented findings indicate rollout and uptake should be monitored as a single action item.",
        "why_now": "Customer and release cues are starting to compound across findings.",
    },
    "narrative_shift": {
        "action": "monitor_narrative_shift",
        "display": "Monitor narrative shift",
        "bucket": "narrative",
        "boost": 0.1,
        "rationale": "Narrative findings cluster around the same story and are better handled as one monitoring action.",
        "why_now": "Narrative framing can shift quickly once corroboration starts to build.",
    },
    "momentum_signal": {
        "action": "increase_monitoring",
        "display": "Increase monitoring",
        "bucket": "momentum",
        "boost": 0.12,
        "rationale": "Momentum findings suggest a story is gaining traction and should be monitored as one consolidated thread.",
        "why_now": "The story is now appearing often enough to justify tighter monitoring.",
    },
}

_BRIEF_TEMPLATES: dict[str, dict[str, str]] = {
    "watch_brief": {
        "title": "Watch brief — what is gaining traction",
        "focus": "cross-cutting developments worth continued monitoring",
    },
    "risk_opportunity_memo": {
        "title": "Risk / opportunity memo — where to lean in or protect",
        "focus": "the clearest upside and downside themes in the current run",
    },
    "weekly_decision_brief": {
        "title": "Decision brief — what changed and what to watch next",
        "focus": "the most decision-relevant developments in the current run",
    },
}


def _find_field(finding: Finding | dict, field: str, default: Any = None) -> Any:
    if isinstance(finding, dict):
        return finding.get(field, default)
    return getattr(finding, field, default)


def _hash_id(prefix: str, values: list[str]) -> str:
    joined = "|".join(sorted(str(v) for v in values if v))
    return f"{prefix}_{hashlib.sha256(joined.encode()).hexdigest()[:10]}"


def _unique(values: list[Any]) -> list[Any]:
    out: list[Any] = []
    seen: set[Any] = set()
    for value in values:
        if value is None or value == "" or value == []:
            continue
        try:
            if value in seen:
                continue
            seen.add(value)
        except TypeError:
            if value in out:
                continue
        out.append(value)
    return out


def _finding_record(finding: Finding | dict) -> dict[str, Any]:
    metadata = dict(_find_field(finding, "metadata", {}) or {})
    return {
        "finding_id": str(_find_field(finding, "finding_id", "") or ""),
        "finding_type": str(_find_field(finding, "finding_type", "narrative_shift") or "narrative_shift"),
        "title": str(_find_field(finding, "display_title") or _find_field(finding, "title") or ""),
        "summary": str(_find_field(finding, "summary") or ""),
        "theme": str(_find_field(finding, "theme") or ""),
        "subject": str(_find_field(finding, "subject") or ""),
        "importance_score": float(_find_field(finding, "importance_score", 0.0) or 0.0),
        "decision_relevance_score": float(_find_field(finding, "decision_relevance_score", 0.0) or 0.0),
        "supporting_event_ids": list(_find_field(finding, "supporting_event_ids") or []),
        "supporting_evidence_ids": list(_find_field(finding, "supporting_evidence_ids") or []),
        "why_it_matters": str(_find_field(finding, "why_it_matters") or ""),
        "watchlist_hits": list(metadata.get("watchlist_hits") or []),
        "topic_hits": list(metadata.get("topic_hits") or []),
        "explain": list(metadata.get("explain") or []),
    }


def _build_signal(finding: Finding | dict, idx: int) -> DecisionSignal:
    record = _finding_record(finding)
    signal_type = {
        "risk_signal": "risk",
        "opportunity_signal": "opportunity",
        "competition_signal": "competition",
        "adoption_signal": "adoption",
        "narrative_shift": "narrative",
        "momentum_signal": "momentum",
    }.get(record["finding_type"], "watch")
    return DecisionSignal(
        signal_id=f"ds_{idx+1}",
        finding_id=record["finding_id"],
        signal_type=signal_type,
        decision_relevance_score=record["decision_relevance_score"],
        supporting_finding_ids=[record["finding_id"]],
        supporting_event_ids=record["supporting_event_ids"],
        supporting_evidence_ids=record["supporting_evidence_ids"],
    )


def _recommendation_group_key(record: dict[str, Any]) -> tuple[str, str]:
    cfg = _ACTION_CONFIG.get(record["finding_type"], _ACTION_CONFIG["momentum_signal"])
    theme = record["theme"] or record["subject"] or cfg["bucket"]
    return cfg["action"], theme


def _build_recommendation(group_key: tuple[str, str], grouped_findings: list[dict[str, Any]], signal_ids: list[str]) -> RecommendationItem:
    action, theme = group_key
    cfg = next(value for value in _ACTION_CONFIG.values() if value["action"] == action)
    finding_ids = _unique([record["finding_id"] for record in grouped_findings])
    event_ids = _unique([eid for record in grouped_findings for eid in record["supporting_event_ids"]])
    evidence_ids = _unique([eid for record in grouped_findings for eid in record["supporting_evidence_ids"]])
    priority_base = sum(record["decision_relevance_score"] for record in grouped_findings) / max(len(grouped_findings), 1)
    importance_avg = sum(record["importance_score"] for record in grouped_findings) / max(len(grouped_findings), 1)
    watchlist_boost = 0.04 if any(record["watchlist_hits"] for record in grouped_findings) else 0.0
    topic_boost = 0.03 if any(record["topic_hits"] for record in grouped_findings) else 0.0
    breadth_boost = min(0.12, 0.04 * max(len(grouped_findings) - 1, 0))
    priority = min(1.0, round(priority_base * 0.55 + importance_avg * 0.25 + cfg["boost"] + watchlist_boost + topic_boost + breadth_boost, 3))
    unique_subjects = _unique([record["subject"] for record in grouped_findings if record["subject"]])
    finding_titles = _unique([record["title"] for record in grouped_findings if record["title"]])
    rationale = cfg["rationale"]
    if len(grouped_findings) > 1:
        rationale += f" This consolidated action combines {len(grouped_findings)} related findings under {theme}."
    elif finding_titles:
        rationale += f" The leading finding is '{finding_titles[0]}'."
    why_now = cfg["why_now"]
    if unique_subjects:
        why_now += f" Focus is concentrated on {', '.join(unique_subjects[:3])}."
    priority_explain = [
        f"0.55*decision_relevance_avg({priority_base:.2f})",
        f"+ 0.25*importance_avg({importance_avg:.2f})",
        f"+ action_boost({cfg['boost']:.2f})",
    ]
    if watchlist_boost:
        priority_explain.append(f"+ watchlist_boost({watchlist_boost:.2f})")
    if topic_boost:
        priority_explain.append(f"+ topic_boost({topic_boost:.2f})")
    if breadth_boost:
        priority_explain.append(f"+ breadth_boost({breadth_boost:.2f})")
    metadata = {
        "display_action": cfg["display"],
        "bucket": cfg["bucket"],
        "consolidated_signal_ids": signal_ids,
        "consolidated_signal_count": len(signal_ids),
        "consolidated_finding_count": len(grouped_findings),
        "consolidated_subjects": unique_subjects,
        "priority_explain": priority_explain,
        "theme": theme,
        "supporting_titles": finding_titles[:5],
    }
    if any(record["watchlist_hits"] for record in grouped_findings):
        metadata["watchlist_hits"] = _unique([hit for record in grouped_findings for hit in record["watchlist_hits"]])
    if any(record["topic_hits"] for record in grouped_findings):
        metadata["topic_hits"] = _unique([hit for record in grouped_findings for hit in record["topic_hits"]])
    return RecommendationItem(
        recommendation_id=_hash_id("rec", [action, theme] + finding_ids),
        signal_id=signal_ids[0] if signal_ids else "",
        recommended_action=action,
        display_action=cfg["display"],
        priority=priority,
        rationale=rationale,
        why_now=why_now,
        requires_human_review=action == "escalate_risk_review",
        supporting_finding_ids=finding_ids,
        supporting_event_ids=event_ids,
        supporting_evidence_ids=evidence_ids,
        metadata=metadata,
    )


def _theme_label(record: dict[str, Any]) -> str:
    return record["theme"] or record["subject"] or record["finding_type"].replace("_", " ")


def _narrative_paragraph(finding_type: str, records: list[dict[str, Any]]) -> str:
    subjects = _unique([record["subject"] for record in records if record["subject"]]) or [_theme_label(records[0])]
    top_titles = _unique([record["title"] for record in records if record["title"]])
    label = {
        "risk_signal": "Risk theme",
        "opportunity_signal": "Opportunity theme",
        "competition_signal": "Competitive theme",
        "adoption_signal": "Adoption theme",
        "narrative_shift": "Narrative theme",
        "momentum_signal": "Momentum theme",
    }.get(finding_type, "Theme")
    first_line = f"{label}: {', '.join(subjects[:3])}."
    if top_titles:
        first_line += f" Leading signal: {top_titles[0]}."
    if len(records) > 1:
        first_line += f" {len(records)} findings reinforce the same story cluster."
    explanations = _unique([ex for record in records for ex in record["explain"]])[:2]
    if explanations:
        first_line += f" Why it matters: {'; '.join(explanations)}."
    return first_line


def _build_briefs(signals: list[DecisionSignal], recommendations: list[RecommendationItem], findings: list[Finding | dict]) -> list[DecisionBrief]:
    if not signals:
        return []
    records = [_finding_record(finding) for finding in findings]
    grouped_by_type: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped_by_type[record["finding_type"]].append(record)
    for finding_type in grouped_by_type:
        grouped_by_type[finding_type].sort(key=lambda item: (-item["decision_relevance_score"], -item["importance_score"], item["finding_id"]))
    recommendation_ids = [rec.recommendation_id for rec in recommendations]
    signal_ids = [sig.signal_id for sig in signals]
    finding_ids = [record["finding_id"] for record in records]
    event_ids = _unique([eid for record in records for eid in record["supporting_event_ids"]])
    evidence_ids = _unique([eid for record in records for eid in record["supporting_evidence_ids"]])
    top_risks = [_theme_label(record) for record in grouped_by_type.get("risk_signal", [])[:3]]
    top_opportunities = [_theme_label(record) for record in grouped_by_type.get("opportunity_signal", [])[:3]]
    top_watch_items = [
        record["title"] or _theme_label(record)
        for finding_type in ("momentum_signal", "narrative_shift", "competition_signal", "adoption_signal")
        for record in grouped_by_type.get(finding_type, [])[:2]
    ]
    section_order = [
        "risk_signal",
        "opportunity_signal",
        "competition_signal",
        "adoption_signal",
        "momentum_signal",
        "narrative_shift",
    ]
    sections = []
    for finding_type in section_order:
        cluster = grouped_by_type.get(finding_type, [])
        if not cluster:
            continue
        sections.append({
            "title": finding_type.replace("_", " ").title(),
            "finding_type": finding_type,
            "paragraph": _narrative_paragraph(finding_type, cluster),
            "finding_ids": [record["finding_id"] for record in cluster[:4]],
        })
    briefs: list[DecisionBrief] = []
    template_inputs = {
        "watch_brief": {
            "summary": f"{len(records)} findings collapsed into {len(recommendations)} action items. Focus on the stories that continue to accumulate corroboration.",
            "focus": "what is changing and what still needs watching",
        },
        "risk_opportunity_memo": {
            "summary": f"Top risks: {len(top_risks)}. Top opportunities: {len(top_opportunities)}. Recommendations have been consolidated to avoid duplicate action items.",
            "focus": "where downside and upside need focused follow-up",
        },
        "weekly_decision_brief": {
            "summary": f"{len(records)} findings now resolve into {len(recommendations)} higher-value recommendations instead of per-signal action stacks.",
            "focus": "the most decision-relevant themes from the latest run",
        },
    }
    brief_recommendation_map = {
        "watch_brief": recommendation_ids[: min(len(recommendation_ids), 5)],
        "risk_opportunity_memo": [
            rec.recommendation_id
            for rec in recommendations
            if rec.recommended_action in {"escalate_risk_review", "pursue_opportunity_validation"}
        ][:5],
        "weekly_decision_brief": recommendation_ids[: min(len(recommendation_ids), 5)],
    }
    for brief_type, template in _BRIEF_TEMPLATES.items():
        summary = template_inputs[brief_type]["summary"]
        focus = template_inputs[brief_type]["focus"]
        narrative_lines = [
            f"This brief summarizes {focus}.",
            *[section["paragraph"] for section in sections[:3]],
        ]
        watch_next = []
        if top_watch_items:
            watch_next.append(f"Continue watching: {', '.join(top_watch_items[:4])}.")
        if recommendations:
            top_actions = [rec.action_title or rec.recommended_action for rec in recommendations[:3]]
            watch_next.append(f"Next actions: {', '.join(top_actions)}.")
        narrative_lines.extend(watch_next)
        selected_recommendations = brief_recommendation_map[brief_type] or recommendation_ids[:3]
        briefs.append(
            DecisionBrief(
                brief_id=_hash_id("dbrief", [brief_type] + signal_ids[:4] + selected_recommendations[:4]),
                brief_type=brief_type,
                title=template["title"],
                summary=summary,
                narrative="\n\n".join(narrative_lines),
                sections=sections,
                key_signals=signal_ids[: min(len(signal_ids), 6)],
                recommendations=selected_recommendations,
                top_risks=top_risks,
                top_opportunities=top_opportunities,
                top_watch_items=_unique(top_watch_items)[:6],
                supporting_finding_ids=finding_ids,
                supporting_event_ids=event_ids,
                supporting_evidence_ids=evidence_ids,
                metadata={
                    "brief_focus": template_inputs[brief_type]["focus"],
                    "n_findings": len(records),
                    "n_recommendations": len(recommendations),
                    "section_count": len(sections),
                    "section_themes": [section["title"] for section in sections],
                },
            )
        )
    return briefs


def run_decision_support(state: TideWatchState) -> dict[str, object]:
    signals: list[DecisionSignal] = []
    findings = state.get("findings") or []
    finding_records: list[dict[str, Any]] = []
    grouped_for_recs: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    signal_ids_by_group: dict[tuple[str, str], list[str]] = defaultdict(list)

    for idx, finding in enumerate(findings):
        signal = _build_signal(finding, idx)
        signals.append(signal)
        record = _finding_record(finding)
        finding_records.append(record)
        group_key = _recommendation_group_key(record)
        grouped_for_recs[group_key].append(record)
        signal_ids_by_group[group_key].append(signal.signal_id)

    recs = [
        _build_recommendation(group_key, grouped_for_recs[group_key], signal_ids_by_group[group_key])
        for group_key in sorted(
            grouped_for_recs,
            key=lambda key: (
                -max(record["decision_relevance_score"] for record in grouped_for_recs[key]),
                -len(grouped_for_recs[key]),
                key[0],
                key[1],
            ),
        )
    ]
    briefs = _build_briefs(signals, recs, findings)
    return {
        "decision_signals": signals,
        "recommendation_items": recs,
        "decision_briefs": briefs,
        "decision_support_metadata": {
            "signals": len(signals),
            "recommendations": len(recs),
            "briefs": len(briefs),
            "findings_in": len(findings),
            "consolidated_actions": len({rec.recommended_action for rec in recs}),
        },
    }
