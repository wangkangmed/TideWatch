"""Shared LangGraph state for the five-layer TideWatch flow."""

from __future__ import annotations

from typing import Any, TypedDict

from tide_watch.models.normalized import NormalizedDocument
from tide_watch.models.pipeline import (
    AlertItem,
    BriefingItem,
    DecisionBrief,
    DecisionSignal,
    EventEvidenceLink,
    EventItem,
    EvidenceItem,
    Finding,
    RecommendationItem,
    TrendSignal,
)
from tide_watch.models.raw import RawFetchBatch


class TideWatchState(TypedDict, total=False):
    run_id: str
    scope: dict[str, Any]
    source_config_path: str
    social_config_path: str
    search_config_path: str
    max_candidates: int
    official_html_max_child_links: int

    # Layer 1: Sources
    raw_batches: list[RawFetchBatch]
    source_errors: list[str]
    source_metadata: dict[str, Any]

    # Layer 2: Evidence
    normalized_docs: list[NormalizedDocument]
    evidence_items: list[EvidenceItem]
    evidence_metadata: dict[str, Any]

    # Layer 3: Events
    events: list[EventItem]
    event_evidence_links: list[EventEvidenceLink]
    events_metadata: dict[str, Any]

    # Layer 4: Intelligence
    trends: list[TrendSignal]
    findings: list[Finding]
    alerts: list[AlertItem]
    briefing_items: list[BriefingItem]
    intelligence_metadata: dict[str, Any]

    # Layer 5: Decision support
    decision_signals: list[DecisionSignal]
    recommendation_items: list[RecommendationItem]
    decision_briefs: list[DecisionBrief]
    decision_support_metadata: dict[str, Any]

    # existing control fields used elsewhere
    should_continue_collect: bool
    coverage_vector: dict[str, Any]
    gap_descriptors: list[dict[str, Any]]
    collect_round: int
