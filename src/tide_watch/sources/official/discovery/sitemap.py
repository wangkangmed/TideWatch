"""Sitemap candidate discovery."""

from __future__ import annotations

from datetime import datetime, timezone
from xml.etree import ElementTree

from tide_watch.config.settings import TideWatchSettings
from tide_watch.sources.official.discovery.network_utils import get_url_text, url_host_resolvable
from tide_watch.sources.official.source_definitions import CandidateURL, SourceDefinition


def _strip_ns(tag: str) -> str:
    return tag.split("}", 1)[-1]


def discover_from_sitemap(
    company: str,
    source: SourceDefinition,
    max_items: int = 100,
    *,
    sitemap_url: str | None = None,
) -> list[CandidateURL]:
    fetched_sitemap_url = (sitemap_url or source.url).strip()
    if not fetched_sitemap_url:
        return []
    settings = TideWatchSettings()
    if settings.official_dns_precheck and not url_host_resolvable(fetched_sitemap_url):
        return []
    try:
        text = get_url_text(
            fetched_sitemap_url,
            timeout=float(settings.official_http_timeout_sec),
            user_agent="TideWatch-Official-Sitemap/1.0",
            retries=max(0, int(settings.official_http_retries)),
        )
    except Exception:  # noqa: BLE001
        return []
    root = ElementTree.fromstring(text)
    now = datetime.now(timezone.utc)
    out: list[CandidateURL] = []

    root_name = _strip_ns(root.tag)
    if root_name == "sitemapindex":
        for sitemap in root.findall(".//{*}sitemap"):
            loc = sitemap.findtext("{*}loc")
            if not loc:
                continue
            nested_source = SourceDefinition(**{**source.model_dump(), "url": loc})
            out.extend(discover_from_sitemap(company, nested_source, max_items=max_items))
            if len(out) >= max_items:
                return out[:max_items]
        return out[:max_items]

    for idx, url_el in enumerate(root.findall(".//{*}url")[:max_items]):
        loc = url_el.findtext("{*}loc")
        if not loc:
            continue
        out.append(
            CandidateURL(
                source_id=source.id,
                company=company,
                url=loc,
                discovered_at=now,
                source_type=source.type,
                hint_doc_type="article",
                priority=80 - idx,
                metadata={"lastmod": url_el.findtext("{*}lastmod"), "sitemap": fetched_sitemap_url},
            )
        )
    return out
