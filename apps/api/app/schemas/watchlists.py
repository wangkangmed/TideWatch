"""Watchlist response schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from .common import PaginatedResponse, PaginationMeta


class WatchlistEntity(BaseModel):
    canonical_name: str
    entity_type: str | None = None
    weight: float = 1.0
    aliases: list[str] = Field(default_factory=list)


class WatchlistTopic(BaseModel):
    topic_name: str
    weight: float = 1.0
    keywords: list[str] = Field(default_factory=list)


class WatchlistSummary(BaseModel):
    watchlist_id: str
    entity_count: int = 0
    topic_count: int = 0
    run_id: str | None = None
    created_at: str | None = None


class WatchlistDetail(WatchlistSummary):
    entities: list[WatchlistEntity] = Field(default_factory=list)
    topics: list[WatchlistTopic] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class WatchlistListResponse(PaginatedResponse[WatchlistSummary]):
    items: list[WatchlistSummary] = Field(default_factory=list)
    pagination: PaginationMeta
