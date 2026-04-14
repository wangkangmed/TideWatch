"""Social source 健康度累计。"""

from __future__ import annotations

from tide_watch.sources.social.models import SocialSourceHealth


def record_attempt(
    health: SocialSourceHealth | None,
    *,
    source_id: str,
    platform: str,
    success: bool,
    error: str | None = None,
) -> SocialSourceHealth:
    h = health or SocialSourceHealth(source_id=source_id, platform=platform)
    h.total_attempts += 1
    if success:
        h.total_successes += 1
        h.last_error = None
    else:
        h.last_error = error
    return h


def record_metadata_fallback(
    health: SocialSourceHealth | None,
    *,
    source_id: str,
    platform: str,
) -> SocialSourceHealth:
    h = health or SocialSourceHealth(source_id=source_id, platform=platform)
    h.metadata_fallback_used += 1
    return h
