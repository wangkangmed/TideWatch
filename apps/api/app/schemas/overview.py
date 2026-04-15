"""Overview / dashboard response schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field

from .alerts import AlertSummary
from .briefs import BriefSummary
from .findings import FindingSummary
from .recommendations import RecommendationSummary
from .runs import RunSummary
from .trends import TrendSummary


class OverviewCounts(BaseModel):
    documents: int = 0
    evidence: int = 0
    events: int = 0
    trends: int = 0
    findings: int = 0
    recommendations: int = 0
    briefs: int = 0
    alerts: int = 0


class OverviewResponse(BaseModel):
    counts: OverviewCounts
    latest_run: RunSummary | None = None
    top_trends: list[TrendSummary] = Field(default_factory=list)
    top_findings: list[FindingSummary] = Field(default_factory=list)
    top_recommendations: list[RecommendationSummary] = Field(default_factory=list)
    recent_alerts: list[AlertSummary] = Field(default_factory=list)
    latest_briefs: list[BriefSummary] = Field(default_factory=list)
