"""Finding response schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from .common import PaginatedResponse, PaginationMeta


class FindingSummary(BaseModel):
    finding_id: str
    subject: str | None = None
    theme: str | None = None
    finding_type: str | None = None
    title: str | None = None
    display_title: str | None = None
    summary: str | None = None
    confidence: float = 0.0
    importance_score: float = 0.0
    decision_relevance_score: float = 0.0
    why_it_matters: str | None = None
    recommended_actions: list[str] = Field(default_factory=list)
    watchlist_hits: list[str] = Field(default_factory=list)
    topic_hits: list[str] = Field(default_factory=list)
    explain: list[str] = Field(default_factory=list)
    event_count: int = 0
    evidence_count: int = 0
    run_id: str | None = None
    created_at: str | None = None


class FindingDetail(FindingSummary):
    trend_id: str | None = None
    supporting_event_ids: list[str] = Field(default_factory=list)
    supporting_evidence_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    related_trend: dict[str, Any] | None = None
    related_events: list[dict[str, Any]] = Field(default_factory=list)
    related_evidence: list[dict[str, Any]] = Field(default_factory=list)
    related_recommendations: list[dict[str, Any]] = Field(default_factory=list)


class FindingListResponse(PaginatedResponse[FindingSummary]):
    items: list[FindingSummary] = Field(default_factory=list)
    pagination: PaginationMeta
