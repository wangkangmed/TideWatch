"""Search discovery models: query/result/candidate and config DTOs."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Literal
from urllib.parse import urlparse

from pydantic import BaseModel, Field

OriginType = Literal["first_party", "community", "external_web"]
DiscoveryChannel = Literal[
    "web_search",
    "official_rss",
    "official_sitemap",
    "official_api",
    "official_html",
    "social_api",
    "backlink_from_social",
]
SearchRoute = Literal[
    "route_to_web_fetch",
    "route_to_official_reconcile",
    "route_to_social_reconcile",
    "skip_low_value",
]


class SearchProviderConfig(BaseModel):
    provider_id: str
    provider: str
    enabled: bool = True
    api_key_ref: str | None = None
    default_limit: int = 10
    timeout_sec: float = 20.0
    region: str | None = None
    language: str | None = None
    base_url: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchMonitorConfig(BaseModel):
    monitor_id: str
    topic: str
    enabled: bool = True
    query_templates: list[str] = Field(default_factory=list)
    providers: list[str] = Field(default_factory=list)
    language: str | None = None
    region: str | None = None
    time_window: str = "7d"
    priority: int = 50
    risk_terms: list[str] = Field(default_factory=list)
    competitors: list[str] = Field(default_factory=list)
    products: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchRegistryConfig(BaseModel):
    search_providers: list[SearchProviderConfig] = Field(default_factory=list)
    search_monitors: list[SearchMonitorConfig] = Field(default_factory=list)


class SearchQuery(BaseModel):
    query_id: str
    monitor_id: str
    topic_id: str
    text: str
    language: str | None = None
    region: str | None = None
    time_window: str = "7d"
    intent: str = "trend_discovery"
    priority: int = 50
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchResultItem(BaseModel):
    query_id: str
    provider: str
    rank: int
    url: str
    title: str | None = None
    snippet: str | None = None
    domain: str
    published_hint: datetime | None = None
    discovered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    raw_metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def with_domain(cls, **kwargs: Any) -> "SearchResultItem":
        url = str(kwargs.get("url") or "")
        kwargs.setdefault("domain", urlparse(url).netloc.lower())
        return cls(**kwargs)


class SearchCandidate(BaseModel):
    candidate_id: str
    url: str
    canonical_url: str
    title_hint: str | None = None
    summary_hint: str | None = None
    published_hint: datetime | None = None
    domain: str
    matched_queries: list[str] = Field(default_factory=list)
    discovery_channels: list[DiscoveryChannel | str] = Field(default_factory=list)
    likely_origin_type: OriginType = "external_web"
    provider_hits: list[str] = Field(default_factory=list)
    score: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class RankedSearchCandidate(BaseModel):
    candidate: SearchCandidate
    route: SearchRoute
    explain: list[str] = Field(default_factory=list)
    fetch_priority: int = 0


def parse_time_window_to_cutoff(window: str, now: datetime | None = None) -> datetime | None:
    raw = (window or "").strip().lower()
    if not raw:
        return None
    base = now or datetime.now(timezone.utc)
    if raw.endswith("d"):
        try:
            return base - timedelta(days=int(raw[:-1]))
        except ValueError:
            return None
    if raw.endswith("h"):
        try:
            return base - timedelta(hours=int(raw[:-1]))
        except ValueError:
            return None
    return None
