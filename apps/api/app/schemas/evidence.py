"""Evidence response schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class EvidenceDetail(BaseModel):
    evidence_id: str
    document_id: str | None = None
    source_id: str | None = None
    origin_type: str | None = None
    title: str | None = None
    canonical_url: str | None = None
    body_text: str | None = None
    source_trace: dict[str, Any] = Field(default_factory=dict)
    document: dict[str, Any] | None = None
    linked_events: list[dict[str, Any]] = Field(default_factory=list)
    run_id: str | None = None
    created_at: str | None = None
