"""SocialConnector：平台差异封装在子类；主流程只依赖本抽象。"""

from __future__ import annotations

from abc import ABC, abstractmethod

from tide_watch.models.raw import RawFetchBatch
from tide_watch.sources.social.models import SocialCandidateItem, SocialCheckpoint, SocialSourceConfig


class SocialConnector(ABC):
    """discover -> 候选项；enrich -> RawFetchBatch（或空批 + errors）。"""

    platform: str

    @abstractmethod
    def discover(
        self,
        source: SocialSourceConfig,
        checkpoint: SocialCheckpoint | None,
    ) -> tuple[list[SocialCandidateItem], SocialCheckpoint | None]:
        """返回候选项与更新后的 checkpoint（无则 None）。"""

    @abstractmethod
    def enrich(
        self,
        items: list[SocialCandidateItem],
        source: SocialSourceConfig,
        checkpoint: SocialCheckpoint | None,
    ) -> RawFetchBatch:
        """将候选项增强为 RawFetchBatch；失败时写入 batch.errors。"""
