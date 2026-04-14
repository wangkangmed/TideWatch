"""采集层原始载荷。"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from tide_watch.models.ids import SourceRef


class RawRecord(BaseModel):
    """单条原始记录（官网/HTML/API/推文快照等）。"""

    source_ref: SourceRef
    fetched_at: datetime
    mime_type: str | None = None
    body_bytes: bytes | None = None
    text: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str = Field(..., description="采集幂等键，同键跳过或覆盖策略由存储决定")


class RawFetchBatch(BaseModel):
    """一次采集批次的容器，便于检查点与审计。"""

    batch_id: str
    records: list[RawRecord] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
