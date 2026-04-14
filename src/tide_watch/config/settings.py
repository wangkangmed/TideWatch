"""Runtime settings (env-driven, lightweight).

This module intentionally avoids a hard dependency on pydantic-settings so
collectors can run in minimal environments.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from tide_watch.sources.official.defaults import (
    ANTHROPIC_NEWS_RSS_MIRROR,
    GOOGLE_AI_BLOG_RSS,
    OPENAI_NEWS_RSS,
)


def _b(name: str, default: bool) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return str(v).strip().lower() in {"1", "true", "yes", "on"}


def _i(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _f(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


@dataclass
class TideWatchSettings:
    # Official RSS connectors
    openai_rss_url: str = os.getenv("TIDEWATCH_OPENAI_RSS_URL", OPENAI_NEWS_RSS)
    anthropic_rss_url: str = os.getenv("TIDEWATCH_ANTHROPIC_RSS_URL", ANTHROPIC_NEWS_RSS_MIRROR)
    google_ai_rss_url: str = os.getenv("TIDEWATCH_GOOGLE_AI_RSS_URL", GOOGLE_AI_BLOG_RSS)
    max_rss_items_per_feed: int = _i("TIDEWATCH_MAX_RSS_ITEMS_PER_FEED", 8)

    # Discovery shaping
    focused_max_candidates: int = _i("TIDEWATCH_FOCUSED_MAX_CANDIDATES", 120)
    focused_source_config: str = os.getenv("TIDEWATCH_FOCUSED_SOURCE_CONFIG", "configs/sources/ai_sources.yaml")

    # Network behavior
    official_http_timeout_sec: float = _f("TIDEWATCH_OFFICIAL_HTTP_TIMEOUT_SEC", 20.0)
    official_http_retries: int = _i("TIDEWATCH_OFFICIAL_HTTP_RETRIES", 1)
    official_dns_precheck: bool = _b("TIDEWATCH_OFFICIAL_DNS_PRECHECK", True)

    # Transport selection mode: balanced | rss_first | rss_only
    official_collection_mode: str = os.getenv("TIDEWATCH_OFFICIAL_COLLECTION_MODE", "balanced").strip().lower()
