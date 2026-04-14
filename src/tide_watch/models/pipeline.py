"""Typed models for pipeline layers 2-5.

Replaces untyped dict[str, Any] in the LangGraph state with
validated Pydantic models for evidence, events, intelligence,
and decision support outputs.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Layer 2: Evidence
# ---------------------------------------------------------------------------

class EvidenceItem(BaseModel):
    evidence_id: str
    doc_id: str
    source_id: str
    source_trace: dict[str, Any] = Field(default_factory=dict)
    text: str = ""


# ---------------------------------------------------------------------------
# Layer 3: Events
# ---------------------------------------------------------------------------

class EventItem(BaseModel):
    event_id: str
    title: str = ""
    source_id: str | None = None
    supporting_evidence_ids: list[str] = Field(default_factory=list)


class EventEvidenceLink(BaseModel):
    link_id: str
    event_id: str
    evidence_id: str
    support_strength: float = 0.7


# ---------------------------------------------------------------------------
# Layer 4: Intelligence
# ---------------------------------------------------------------------------

class TrendSignal(BaseModel):
    trend_id: str
    title: str | None = None
    strength_score: float = 0.0
    corroboration_score: float = 0.0
    supporting_event_ids: list[str] = Field(default_factory=list)


class Finding(BaseModel):
    finding_id: str
    trend_id: str | None = None
    finding_type: str = "watch_signal"
    importance_score: float = 0.0
    decision_relevance_score: float = 0.0
    supporting_event_ids: list[str] = Field(default_factory=list)
    supporting_evidence_ids: list[str] = Field(default_factory=list)


class AlertItem(BaseModel):
    alert_id: str
    finding_id: str
    level: str = "medium"


class BriefingItem(BaseModel):
    briefing_id: str
    finding_id: str
    title: str = ""


# ---------------------------------------------------------------------------
# Layer 5: Decision Support
# ---------------------------------------------------------------------------

class DecisionSignal(BaseModel):
    signal_id: str
    finding_id: str
    signal_type: str = "watch"
    decision_relevance_score: float = 0.0
    supporting_finding_ids: list[str] = Field(default_factory=list)
    supporting_event_ids: list[str] = Field(default_factory=list)
    supporting_evidence_ids: list[str] = Field(default_factory=list)


class RecommendationItem(BaseModel):
    recommendation_id: str
    signal_id: str
    recommended_action: str = "increase_monitoring"
    priority: float = 0.0
    supporting_finding_ids: list[str] = Field(default_factory=list)
    supporting_event_ids: list[str] = Field(default_factory=list)
    supporting_evidence_ids: list[str] = Field(default_factory=list)


class DecisionBrief(BaseModel):
    brief_id: str
    brief_type: str = "watch_brief"
    title: str = ""
    key_signals: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
