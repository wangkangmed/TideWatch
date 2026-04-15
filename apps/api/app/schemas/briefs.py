"""Brief / Briefing response schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from .common import PaginatedResponse, PaginationMeta


class BriefSummary(BaseModel):
    brief_id: str
    brief_type: str | None = None
    title: str | None = None
    summary: str | None = None
    signal_count: int = 0
    recommendation_count: int = 0
    run_id: str | None = None
    created_at: str | None = None


class BriefDetail(BriefSummary):
    key_signals: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    top_risks: list[str] = Field(default_factory=list)
    top_opportunities: list[str] = Field(default_factory=list)
    top_watch_items: list[str] = Field(default_factory=list)
    supporting_finding_ids: list[str] = Field(default_factory=list)
    supporting_event_ids: list[str] = Field(default_factory=list)
    supporting_evidence_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class BriefingItemSummary(BaseModel):
    briefing_item_id: str
    title: str | None = None
    summary: str | None = None
    theme: str | None = None
    importance_score: float = 0.0
    decision_relevance: float = 0.0
    evidence_count: int = 0
    run_id: str | None = None
    created_at: str | None = None


class BriefListResponse(PaginatedResponse[BriefSummary]):
    items: list[BriefSummary] = Field(default_factory=list)
    pagination: PaginationMeta
