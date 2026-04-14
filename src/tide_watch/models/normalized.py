"""Compatibility normalized document model."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from tide_watch.models.ids import SourceRef


class NormalizedDocument(BaseModel):
    doc_id: str
    source_ref: SourceRef
    source_id: str | None = None
    origin_type: str | None = None
    discovery_channels: list[str] = Field(default_factory=list)
    title: str | None = None
    canonical_url: str | None = None
    published_at: datetime | None = None
    updated_at: datetime | None = None
    language: str | None = None
    body_text: str = ""
    structured_fields: dict[str, Any] = Field(default_factory=dict)
    page_type: str | None = None
    quality_score: float | None = None
    trust_tier: int | None = None
    raw_metadata: dict[str, Any] = Field(default_factory=dict)
    fingerprint: str | None = None

    @property
    def document_id(self) -> str:
        return self.doc_id
