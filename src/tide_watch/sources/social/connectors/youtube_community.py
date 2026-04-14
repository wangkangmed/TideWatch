"""YouTube Community：预留（YouTube Data API / RSS）。"""

from __future__ import annotations

import logging

from tide_watch.models.raw import RawFetchBatch
from tide_watch.sources.social.connectors.base import SocialConnector
from tide_watch.sources.social.models import SocialCandidateItem, SocialCheckpoint, SocialSourceConfig

logger = logging.getLogger(__name__)


class YouTubeCommunityConnector(SocialConnector):
    platform = "youtube_community"

    def discover(
        self,
        source: SocialSourceConfig,
        checkpoint: SocialCheckpoint | None,
    ) -> tuple[list[SocialCandidateItem], SocialCheckpoint | None]:
        logger.info("youtube_community_connector_stub source=%s", source.source_id)
        return [], checkpoint

    def enrich(
        self,
        items: list[SocialCandidateItem],
        source: SocialSourceConfig,
        checkpoint: SocialCheckpoint | None,
    ) -> RawFetchBatch:
        _ = checkpoint
        _ = items
        return RawFetchBatch(
            batch_id=f"social-youtube-{source.source_id}-stub",
            records=[],
            errors=["youtube_community: stub — 请用 YouTube Data API 或频道 RSS 接入"],
        )
