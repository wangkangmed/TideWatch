"""RSS/Atom candidate discovery."""

from __future__ import annotations

from datetime import datetime, timezone

import feedparser

from tide_watch.config.settings import TideWatchSettings
from tide_watch.sources.official.discovery.network_utils import (
    classify_network_error,
    get_url_text,
    url_host_resolvable,
)
from tide_watch.web.date_parser import parse_feed_date_string
from tide_watch.sources.official.source_definitions import CandidateURL, SourceDefinition
from tide_watch.sources.official.strategies.source_strategy import strategy_metadata_for_candidate


def discover_from_rss(
    company: str,
    source: SourceDefinition,
    max_items: int = 30,
    *,
    feed_url: str | None = None,
) -> list[CandidateURL]:
    url = (feed_url or source.url).strip()
    if not url:
        return []
    settings = TideWatchSettings()
    if settings.official_dns_precheck and not url_host_resolvable(url):
        return []
    try:
        text = get_url_text(
            url,
            timeout=float(settings.official_http_timeout_sec),
            user_agent="TideWatch-Official-RSS/1.0",
            retries=max(0, int(settings.official_http_retries)),
        )
    except Exception as exc:  # noqa: BLE001
        # Let caller continue other transports for this source.
        _ = classify_network_error(exc)
        return []

    parsed = feedparser.parse(text)
    out: list[CandidateURL] = []
    strat_meta = strategy_metadata_for_candidate(source)
    for idx, entry in enumerate(list(parsed.entries or [])[:max_items]):
        link = getattr(entry, "link", None)
        if not link:
            continue
        raw_date = getattr(entry, "published", None) or getattr(entry, "updated", None)
        dt = parse_feed_date_string(str(raw_date) if raw_date else None)
        meta: dict = {
            "title": getattr(entry, "title", ""),
            "snippet": getattr(entry, "summary", ""),
            "date": raw_date,
            "feed_url": url,
            "discovery_method": "feed",
            **strat_meta,
        }
        if dt:
            meta["published_at"] = dt.isoformat()
        out.append(
            CandidateURL(
                source_id=source.id,
                company=company,
                url=str(link),
                discovered_at=datetime.now(timezone.utc),
                source_type=source.type,
                hint_doc_type="article",
                priority=90 - idx,
                metadata=meta,
            )
        )
    return out
