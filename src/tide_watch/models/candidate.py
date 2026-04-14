"""Discovery 阶段统一候选（可映射为 LangGraph CandidateURL / RawRecord）。"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field

TransportType = Literal["rss", "sitemap", "rest_api", "html_listing"]


class CandidateItem(BaseModel):
    source_id: str
    provider: str = ""
    transport: TransportType = "html_listing"
    external_id: str = ""
    url: str
    title: str | None = None
    summary: str | None = None
    published_at: datetime | None = None
    discovered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    parent_url: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
