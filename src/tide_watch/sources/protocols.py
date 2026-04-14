"""
后续接入不同 source/provider 时实现这些 Protocol / ABC。
节点只依赖协议，不依赖具体爬虫/ API 实现。
"""

from abc import ABC, abstractmethod
from typing import Any, Protocol, runtime_checkable

from tide_watch.models.normalized import NormalizedDocument
from tide_watch.models.raw import RawFetchBatch


@runtime_checkable
class FetchCursor(Protocol):
    """分页/增量游标：序列化存入 checkpoint。"""

    def to_checkpoint_blob(self) -> dict[str, Any]: ...
    @classmethod
    def from_checkpoint_blob(cls, blob: dict[str, Any]) -> "FetchCursor": ...


class SourceConnector(ABC):
    """
    单一 provider 的采集入口：官网 RSS、社媒 API、搜索 API 等各自实现。

    幂等：同一 (scope, cursor) 重复调用应返回稳定或可检测的重复批次。
    """

    provider_id: str

    @abstractmethod
    async def fetch(self, scope: dict[str, Any], cursor: FetchCursor | None) -> RawFetchBatch: ...

    @abstractmethod
    def merge_cursor(self, previous: FetchCursor | None, batch: RawFetchBatch) -> FetchCursor | None:
        """返回下一游标；无更多数据时返回 None。"""


class Normalizer(ABC):
    """Raw -> NormalizedDocument；纯代码或可插拔 LLM 摘要由实现决定。"""

    @abstractmethod
    def normalize(self, batch: RawFetchBatch) -> list[NormalizedDocument]: ...


class DedupeClusterService(ABC):
    """去重 + 聚类：通常纯代码（hash/SimHash/向量），可调用嵌入服务。"""

    @abstractmethod
    def cluster(self, docs: list[NormalizedDocument]) -> tuple[dict[str, list[str]], dict[str, Any]]:
        """返回 (cluster_id -> doc_ids, stats)"""


class CoverageAnalyzer(ABC):
    """对照 topic_scope 评估覆盖；可 LLM 辅助 gap 描述。"""

    @abstractmethod
    def analyze(
        self,
        scope: dict[str, Any],
        clusters: dict[str, list[str]],
        docs_by_id: dict[str, NormalizedDocument],
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        """返回 (coverage_vector, gap_descriptors)"""


class BackfillPlanner(ABC):
    """根据 gap 生成补采请求（搜索词、时间窗、特定 URL）。"""

    @abstractmethod
    def plan(self, gaps: list[dict[str, Any]], scope: dict[str, Any]) -> list[dict[str, Any]]:
        """返回 backfill_requests，下游采集节点消费。"""
