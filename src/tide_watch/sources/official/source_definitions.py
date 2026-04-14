"""YAML 官方源定义（与 configs/sources/ai_sources.yaml 对齐）。"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from tide_watch.models.ingestion import SourceAccessMode, SourceStrategy

TransportType = Literal["rss", "sitemap", "rest_api", "html_listing"]


class OfficialTransportConfig(BaseModel):
    """单条 transport 策略（可与 legacy 字段并存）。"""

    transport: TransportType
    enabled: bool = True
    priority: int = 50
    # rss / sitemap / html_listing
    url: str | None = None
    # rest_api
    base_url: str | None = None
    list_path: str | None = None
    headers: dict[str, str] = Field(default_factory=dict)
    # JSON list 解析：点分路径，如 data.items；留空则尝试顶层 list 或常见键
    items_path: str | None = None
    field_map: dict[str, str] = Field(default_factory=dict)


class SourceDefinition(BaseModel):
    id: str
    type: str
    url: str
    access: SourceAccessMode = "listing_only"
    priority: str = "medium"
    enabled: bool = True
    notes: str | None = None
    display_name: str | None = None
    source_strategy: SourceStrategy | None = None
    preferred_discovery_mode: Literal["listing", "feed", "sitemap", "auto"] = "auto"
    follow_detail_pages: bool | None = None
    metadata_fallback: bool | None = None
    protected_policy: Literal["degrade", "skip_detail"] = "degrade"
    content_quality_expectation: Literal["high", "medium", "low"] = "medium"
    listing_selectors: dict[str, Any] = Field(default_factory=dict)
    # 多 transport：为空时由 legacy type/url/rss_url/sitemap_url/api_* 推断
    strategies: list[OfficialTransportConfig] = Field(default_factory=list)
    transport_collection_mode: Literal["combine", "prefer_fallback"] = "combine"
    enrichment: dict[str, Any] = Field(default_factory=dict)
    # 可选：附加 transport（与主 url 并存）
    rss_url: str | None = None
    sitemap_url: str | None = None
    # rest_api 最小配置（可选）
    api_list_url: str | None = None
    api_headers: dict[str, str] = Field(default_factory=dict)
    api_items_path: str | None = None
    api_field_map: dict[str, str] = Field(default_factory=dict)


class CompanySourceConfig(BaseModel):
    company: str
    tags: list[str] = Field(default_factory=list)
    sources: list[SourceDefinition] = Field(default_factory=list)


class SourceRegistryConfig(BaseModel):
    companies: list[CompanySourceConfig] = Field(default_factory=list)


class CandidateURL(BaseModel):
    """LangGraph 状态内候选 URL（与 CandidateItem 可互转）。"""

    source_id: str
    company: str
    url: str
    discovered_at: datetime
    source_type: str
    hint_doc_type: str | None = None
    priority: int = 50
    metadata: dict[str, Any] = Field(default_factory=dict)


class CandidateSet(BaseModel):
    items: list[CandidateURL] = Field(default_factory=list)
