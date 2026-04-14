"""Alert response schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from .common import PaginatedResponse, PaginationMeta


class AlertSummary(BaseModel):
    alert_id: str
    level: str | None = None
    finding_id: str | None = None
    signal_type: str | None = None
    title: str | None = None
    summary: str | None = None
    importance_score: float = 0.0
    run_id: str | None = None
    created_at: str | None = None


class AlertListResponse(PaginatedResponse[AlertSummary]):
    items: list[AlertSummary] = Field(default_factory=list)
    pagination: PaginationMeta
