"""X / Twitter：需受支持 API 与凭证；本仓库不提供抓取绕过。"""

from __future__ import annotations

import logging

from tide_watch.models.raw import RawFetchBatch
from tide_watch.sources.social.connectors.base import SocialConnector
from tide_watch.sources.social.models import SocialCandidateItem, SocialCheckpoint, SocialSourceConfig

logger = logging.getLogger(__name__)


class XConnector(SocialConnector):
    platform = "x"

    def discover(
        self,
        source: SocialSourceConfig,
        checkpoint: SocialCheckpoint | None,
    ) -> tuple[list[SocialCandidateItem], SocialCheckpoint | None]:
        logger.info(
            "x_connector_pending source=%s auth_ref=%s — 需要官方 API 与 auth_ref，当前未接入",
            source.source_id,
            source.auth_ref,
        )
        prev = dict(checkpoint.blob) if checkpoint else {}
        return [], SocialCheckpoint(source_id=source.source_id, platform="x", blob=prev)

    def enrich(
        self,
        items: list[SocialCandidateItem],
        source: SocialSourceConfig,
        checkpoint: SocialCheckpoint | None,
    ) -> RawFetchBatch:
        _ = items
        return RawFetchBatch(
            batch_id=f"social-x-{source.source_id}-pending",
            records=[],
            errors=["x: pending_official_api — 请配置 X API v2 与 auth_ref 后实现 connector"],
        )
