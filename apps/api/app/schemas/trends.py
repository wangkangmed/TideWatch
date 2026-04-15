"""Trend response schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from .common import PaginatedResponse, PaginationMeta


class TrendSummary(BaseModel):
    trend_id: str
    subject: str | None = None
    theme: str | None = None
    title: str | None = None
    display_title: str | None = None
    summary: str | None = None
    trend_type: str | None = None
    direction: str | None = None
    strength_score: float = 0.0
    novelty_score: float = 0.0
    corroboration_score: float = 0.0
    confidence: float = 0.0
    why_it_matters: str | None = None
    event_count: int = 0
    evidence_count: int = 0
    document_count: int = 0
    explain: list[str] = Field(default_factory=list)
    merge_reasons: list[str] = Field(default_factory=list)
    run_id: str | None = None
    created_at: str | None = None


class TrendDetail(TrendSummary):
    window: dict[str, Any] | None = None
    event_ids: list[str] = Field(default_factory=list)
    bundle_ids: list[str] = Field(default_factory=list)
    supporting_evidence_ids: list[str] = Field(default_factory=list)
    supporting_document_ids: list[str] = Field(default_factory=list)
    canonical_urls: list[str] = Field(default_factory=list)
    related_events: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class TrendListResponse(PaginatedResponse[TrendSummary]):
    items: list[TrendSummary] = Field(default_factory=list)
    pagination: PaginationMeta
