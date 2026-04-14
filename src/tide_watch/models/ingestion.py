"""官网/HTML 采集管线共用 DTO（原 focused.models 中的抓取/抽取/归一化类型）。"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

SourceStrategy = Literal["fulltext_preferred", "structured_index", "metadata_preferred", "protected"]

SourceAccessMode = Literal[
    "direct_html",
    "rendered_html",
    "api",
    "listing_only",
    "feed_only",
    "metadata_only",
    "skip",
]

BlockType = Literal[
    "success",
    "redirect",
    "origin_forbidden",
    "cloudflare_challenge",
    "cloudflare_block",
    "unknown_403",
    "rate_limited",
    "timeout",
    "parse_error",
    "unsupported_content_type",
    "network_error",
]


class FetchPlan(BaseModel):
    source_id: str
    company: str
    url: str
    mode: SourceAccessMode
    reason: str
    retryable: bool = False
    allowed: bool = True
    notes: str | None = None


class FetchResult(BaseModel):
    source_id: str
    company: str
    url: str
    final_url: str | None = None
    status_code: int | None = None
    content_type: str | None = None
    headers: dict[str, str] = Field(default_factory=dict)
    raw_text: str | None = None
    raw_html: str | None = None
    detected_block_type: BlockType = "success"
    detected_platform: str = "none"
    fetch_mode: SourceAccessMode = "direct_html"
    success: bool = False
    retryable: bool = False
    error: str | None = None
    discovered_metadata: dict[str, Any] = Field(default_factory=dict)


class ExtractedDocument(BaseModel):
    source_id: str
    company: str
    url: str
    canonical_url: str | None = None
    title: str | None = None
    published_at: datetime | None = None
    updated_at: datetime | None = None
    author: str | None = None
    body_text: str = ""
    summary: str | None = None
    tags: list[str] = Field(default_factory=list)
    language: str | None = None
    outbound_links: list[str] = Field(default_factory=list)
    extraction_quality_score: float = 0.0
    extracted_fields: dict[str, Any] = Field(default_factory=dict)
    extraction_notes: list[str] = Field(default_factory=list)
    raw_metadata: dict[str, Any] = Field(default_factory=dict)


class FocusedNormalizedDocument(BaseModel):
    document_id: str
    company: str
    source_id: str
    source_type: str
    url: str
    canonical_url: str | None = None
    title: str | None = None
    published_at: datetime | None = None
    updated_at: datetime | None = None
    ingested_at: datetime
    doc_type: str | None = None
    content_text: str = ""
    summary: str | None = None
    tags: list[str] = Field(default_factory=list)
    language: str | None = None
    access_mode: str
    fetch_status: int | None = None
    blocked_by: str | None = None
    quality_score: float = 0.0
    content_hash: str
    raw_metadata: dict[str, Any] = Field(default_factory=dict)


class SourceHealth(BaseModel):
    source_id: str
    success_rate: float = 0.0
    last_success_at: datetime | None = None
    last_failure_at: datetime | None = None
    failure_reason: str | None = None
    last_block_reason: str | None = None
    anti_bot_score: float = 0.0
    preferred_mode: SourceAccessMode = "listing_only"
    recommended_mode: str | None = None
    enabled: bool = True
    notes: str | None = None
    total_attempts: int = 0
    total_successes: int = 0
    detail_fetch_attempts: int = 0
    detail_fetch_successes: int = 0
    metadata_fallback_docs: int = 0
    protected_events: int = 0
    detail_success_rate: float = 0.0
    metadata_fallback_rate: float = 0.0
    protected_rate: float = 0.0
    documents_ingested: int = 0


class FetchAttempt(BaseModel):
    source_id: str
    url: str
    status_code: int | None = None
    block_type: BlockType = "success"
    fetch_mode: SourceAccessMode = "direct_html"
    retryable: bool = False
    error: str | None = None
    created_at: datetime


class IngestionRunStats(BaseModel):
    discovered: int = 0
    fetched: int = 0
    normalized: int = 0
    deduped: int = 0
