"""LinkedIn：预留 connector，公开流通常需授权。"""

from __future__ import annotations

import logging

from tide_watch.models.raw import RawFetchBatch
from tide_watch.sources.social.connectors.base import SocialConnector
from tide_watch.sources.social.models import SocialCandidateItem, SocialCheckpoint, SocialSourceConfig

logger = logging.getLogger(__name__)


class LinkedInConnector(SocialConnector):
    platform = "linkedin"

    def discover(
        self,
        source: SocialSourceConfig,
        checkpoint: SocialCheckpoint | None,
    ) -> tuple[list[SocialCandidateItem], SocialCheckpoint | None]:
        logger.info("linkedin_connector_stub source=%s", source.source_id)
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
            batch_id=f"social-linkedin-{source.source_id}-stub",
            records=[],
            errors=["linkedin: stub — 需官方 Marketing/Community API"],
        )
