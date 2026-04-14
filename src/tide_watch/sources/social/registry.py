"""按 platform 解析 SocialConnector 实例。"""

from __future__ import annotations

from tide_watch.sources.social.connectors.base import SocialConnector
from tide_watch.sources.social.connectors.hackernews import HackerNewsConnector
from tide_watch.sources.social.connectors.linkedin import LinkedInConnector
from tide_watch.sources.social.connectors.reddit import RedditConnector
from tide_watch.sources.social.connectors.x import XConnector
from tide_watch.sources.social.connectors.youtube_community import YouTubeCommunityConnector
from tide_watch.sources.social.models import SocialSourceConfig


def get_connector_for_source(source: SocialSourceConfig) -> SocialConnector:
    p = source.platform
    if p == "reddit":
        return RedditConnector()
    if p == "hackernews":
        return HackerNewsConnector()
    if p == "x":
        return XConnector()
    if p == "linkedin":
        return LinkedInConnector()
    if p == "youtube_community":
        return YouTubeCommunityConnector()
    raise KeyError(f"unknown social platform: {p}")
