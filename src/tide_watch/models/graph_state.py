"""Shared LangGraph state for the five-layer TideWatch flow."""

from __future__ import annotations

from typing import Any, TypedDict

from tide_watch.models.normalized import NormalizedDocument
from tide_watch.models.raw import RawFetchBatch


class TideWatchState(TypedDict, total=False):
    run_id: str
    scope: dict[str, Any]
    source_config_path: str
    social_config_path: str
    search_config_path: str
    max_candidates: int

    # Layer 1: Sources
    raw_batches: list[RawFetchBatch]
    source_errors: list[str]
    source_metadata: dict[str, Any]

    # Layer 2: Evidence
    normalized_docs: list[NormalizedDocument]
    evidence_items: list[dict[str, Any]]
    evidence_metadata: dict[str, Any]

    # Layer 3: Events
    events: list[dict[str, Any]]
    event_evidence_links: list[dict[str, Any]]
    events_metadata: dict[str, Any]

    # Layer 4: Intelligence
    trends: list[dict[str, Any]]
    findings: list[dict[str, Any]]
    alerts: list[dict[str, Any]]
    briefing_items: list[dict[str, Any]]
    intelligence_metadata: dict[str, Any]

    # Layer 5: Decision support
    decision_signals: list[dict[str, Any]]
    recommendation_items: list[dict[str, Any]]
    decision_briefs: list[dict[str, Any]]
    decision_support_metadata: dict[str, Any]

    # existing control fields used elsewhere
    should_continue_collect: bool
    coverage_vector: dict[str, Any]
    gap_descriptors: list[dict[str, Any]]
    collect_round: int
