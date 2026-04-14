"""Social 采集统一 DTO：配置、候选项、检查点。"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

SocialPlatform = Literal["reddit", "hackernews", "x", "linkedin", "youtube_community"]


class SocialSourceConfig(BaseModel):
    """单条社交流源配置（与 YAML `social_sources` 对齐）。"""

    source_id: str
    platform: SocialPlatform
    source_type: str
    enabled: bool = True
    priority: int = 50
    strategy: str = "fulltext_preferred"
    auth_ref: str | None = None
    query: str | None = None
    handle_or_community: str | None = None
    include_comments: bool = False
    max_items: int = 20
    metadata_fallback: bool = True
    trust_tier: int = 2


class SocialRegistryConfig(BaseModel):
    """仅社交流源列表（可从主 YAML 拆出或内嵌）。"""

    social_sources: list[SocialSourceConfig] = Field(default_factory=list)


class SocialCheckpoint(BaseModel):
    """connector 可序列化游标，存入下一轮或外部存储。"""

    source_id: str
    platform: SocialPlatform
    blob: dict[str, Any] = Field(default_factory=dict)

    def to_blob(self) -> dict[str, Any]:
        return {"source_id": self.source_id, "platform": self.platform, "blob": dict(self.blob)}

    @classmethod
    def from_blob(cls, data: dict[str, Any]) -> SocialCheckpoint:
        plat_raw = data.get("platform") or "reddit"
        plat = str(plat_raw)
        allowed: tuple[str, ...] = ("reddit", "hackernews", "x", "linkedin", "youtube_community")
        if plat not in allowed:
            plat = "reddit"
        return cls(
            source_id=str(data.get("source_id") or ""),
            platform=plat,  # type: ignore[arg-type]
            blob=dict(data.get("blob") or {}),
        )


class SocialCandidateItem(BaseModel):
    """Discovery 阶段统一输出。"""

    source_id: str
    platform: SocialPlatform
    source_type: str
    external_id: str
    url: str
    author_handle: str | None = None
    title: str | None = None
    text: str = ""
    summary: str | None = None
    published_at: datetime | None = None
    discovered_at: datetime
    engagement: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SocialSourceHealth(BaseModel):
    """轻量健康度：与 official SourceHealth 解耦，结构相近便于后续合并 UI。"""

    source_id: str
    platform: str
    total_attempts: int = 0
    total_successes: int = 0
    last_error: str | None = None
    metadata_fallback_used: int = 0

    @property
    def success_rate(self) -> float:
        if self.total_attempts <= 0:
            return 0.0
        return self.total_successes / self.total_attempts
