"""跨层稳定标识：运行、来源、内容指纹。"""

from typing import NewType

from pydantic import BaseModel, Field

RunId = NewType("RunId", str)


class SourceRef(BaseModel):
    """逻辑来源引用：用于幂等与追溯。"""

    provider_id: str = Field(..., description="注册表中的 provider，如 official_acme_rss")
    external_id: str = Field(..., description="provider 侧稳定 id 或 URL 规范化键")
    shard_hint: str | None = Field(default=None, description="分片/租户键，可选")


class ContentFingerprint(BaseModel):
    """标准化后用于去重/聚类的指纹。"""

    hash_primary: str
    hash_simhash: str | None = None
    embedding_id: str | None = None
