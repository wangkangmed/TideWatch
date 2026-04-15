"""Event response schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from .common import PaginatedResponse, PaginationMeta


class EventSummary(BaseModel):
    event_id: str
    event_type: str | None = None
    subject: str | None = None
    canonical_title: str | None = None
    significance_score: float = 0.0
    confidence: float = 0.0
    evidence_count: int = 0
    run_id: str | None = None
    created_at: str | None = None


class EventDetail(EventSummary):
    object: str | None = None
    event_time: str | None = None
    time_precision: str | None = None
    status: str | None = None
    supporting_evidence_ids: list[str] = Field(default_factory=list)
    entities: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    evidence_items: list[dict[str, Any]] = Field(default_factory=list)


class EventListResponse(PaginatedResponse[EventSummary]):
    items: list[EventSummary] = Field(default_factory=list)
    pagination: PaginationMeta
