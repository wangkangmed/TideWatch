"""Run response schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from .common import PaginatedResponse, PaginationMeta


class RunSummary(BaseModel):
    run_id: str
    status: str | None = None
    topic_query: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    document_count: int = 0
    event_count: int = 0
    trend_count: int = 0
    finding_count: int = 0
    recommendation_count: int = 0
    brief_count: int = 0


class RunDetail(RunSummary):
    metadata: dict[str, Any] = Field(default_factory=dict)


class RunListResponse(PaginatedResponse[RunSummary]):
    items: list[RunSummary] = Field(default_factory=list)
    pagination: PaginationMeta
