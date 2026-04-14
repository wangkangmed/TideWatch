"""LangGraph state for focused ingestion."""

from __future__ import annotations

from typing import Any, TypedDict

from tide_watch.models.ingestion import (
    ExtractedDocument,
    FetchAttempt,
    FetchPlan,
    FetchResult,
    FocusedNormalizedDocument,
    IngestionRunStats,
    SourceHealth,
)
from tide_watch.sources.official.source_definitions import CandidateURL


class IngestionState(TypedDict, total=False):
    run_id: str
    source_config_path: str
    max_candidates: int
    # 每个列表种子页最多展开多少条子链接（第二级）
    listing_max_child_links: int
    source_config: dict[str, Any]
    candidates: list[CandidateURL]
    canonical_candidates: list[CandidateURL]
    fetch_plans: list[FetchPlan]
    fetch_results: list[FetchResult]
    fetch_attempts: list[FetchAttempt]
    extracted_docs: list[ExtractedDocument]
    normalized_docs: list[FocusedNormalizedDocument]
    deduped_docs: list[FocusedNormalizedDocument]
    persisted_docs: list[str]
    source_health: dict[str, SourceHealth]
    errors: list[str]
    attempts: int
    stats: IngestionRunStats
