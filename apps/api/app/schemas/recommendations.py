"""Recommendation response schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from .common import PaginatedResponse, PaginationMeta


class RecommendationSummary(BaseModel):
    recommendation_id: str
    signal_id: str | None = None
    recommended_action: str | None = None
    priority: float = 0.0
    rationale: str | None = None
    why_now: str | None = None
    requires_human_review: bool = False
    finding_count: int = 0
    event_count: int = 0
    evidence_count: int = 0
    run_id: str | None = None
    created_at: str | None = None


class RecommendationDetail(RecommendationSummary):
    supporting_finding_ids: list[str] = Field(default_factory=list)
    supporting_event_ids: list[str] = Field(default_factory=list)
    supporting_evidence_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    related_signal: dict[str, Any] | None = None
    related_findings: list[dict[str, Any]] = Field(default_factory=list)


class RecommendationListResponse(PaginatedResponse[RecommendationSummary]):
    items: list[RecommendationSummary] = Field(default_factory=list)
    pagination: PaginationMeta
