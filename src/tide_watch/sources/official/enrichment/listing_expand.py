"""第二级：从列表/目录页 HTML 抽取条目级候选（链接 + 列表侧标题等）。"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from urllib.parse import urlparse

from tide_watch.config.settings import TideWatchSettings
from tide_watch.sources.official.discovery.network_utils import (
    classify_network_error,
    get_url_text,
    url_host_resolvable,
)
from tide_watch.sources.official.discovery.listing_expand_legacy import extract_article_links_from_listing_html
from tide_watch.sources.official.discovery.listing_items import draft_to_listing_metadata, extract_listing_item_drafts
from tide_watch.sources.official.source_definitions import CandidateURL, SourceDefinition

logger = logging.getLogger(__name__)


def _strategy_and_follow_for_child(seed_url: str, child_url: str, base_meta: dict) -> tuple[str, bool]:
    """structured_index 根列表走索引抽取；子条目 URL 走正文抓取。"""
    ps = str(base_meta.get("source_strategy") or "")
    follow = bool(base_meta.get("follow_detail_pages", True))
    if ps != "structured_index":
        return ps, follow
    sp = urlparse(seed_url).path.rstrip("/")
    cp = urlparse(child_url).path.rstrip("/")
    if cp == sp:
        return ps, follow
    if not cp.startswith(sp + "/") and cp != sp:
        return "fulltext_preferred", True
    tail = cp[len(sp) :].lstrip("/") if cp.startswith(sp + "/") else cp
    if not tail:
        return ps, follow
    if "/" in tail or len(tail) > 5:
        return "fulltext_preferred", True
    return ps, follow


def expand_listing_seed(
    seed: CandidateURL,
    *,
    source: SourceDefinition | None = None,
    max_child_links: int = 15,
    timeout: float = 25.0,
    user_agent: str = "TideWatch-Ingestion/1.0 (+listing-expand)",
) -> list[CandidateURL]:
    """GET 种子列表页，抽取条目级 URL，生成子候选。"""
    children: list[CandidateURL] = []
    settings = TideWatchSettings()
    if settings.official_dns_precheck and not url_host_resolvable(seed.url):
        logger.warning("listing_expand_dns_unresolvable url=%s", seed.url)
        return children
    try:
        html = get_url_text(
            seed.url,
            timeout=float(timeout if timeout > 0 else settings.official_http_timeout_sec),
            user_agent=user_agent,
            retries=max(0, int(settings.official_http_retries)),
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "listing_expand_fetch_failed url=%s kind=%s err=%s",
            seed.url,
            classify_network_error(exc),
            exc,
        )
        return children

    drafts = extract_listing_item_drafts(seed.url, html, source=source, max_items=max_child_links)
    now = datetime.now(timezone.utc)
    access = str(seed.metadata.get("access") or "listing_only")
    base_meta = dict(seed.metadata or {})

    if drafts:
        for d in drafts:
            lm = draft_to_listing_metadata(d, seed.url)
            strat, follow = _strategy_and_follow_for_child(seed.url, d.url, base_meta)
            child_meta = {
                **base_meta,
                **lm,
                "seed": False,
                "from_listing_expansion": True,
                "access": access,
                "source_strategy": strat,
                "follow_detail_pages": follow,
            }
            children.append(
                CandidateURL(
                    source_id=seed.source_id,
                    company=seed.company,
                    url=d.url,
                    discovered_at=now,
                    source_type=seed.source_type,
                    hint_doc_type="article",
                    priority=max(1, seed.priority - 5),
                    metadata=child_meta,
                )
            )
        return children

    pairs = extract_article_links_from_listing_html(seed.url, html, max_links=max_child_links)
    for url, _anchor in pairs:
        strat, follow = _strategy_and_follow_for_child(seed.url, url, base_meta)
        child_meta = {
            **base_meta,
            "discovery_method": "listing",
            "parent_listing_url": seed.url,
            "title": None,
            "snippet": "",
            "detail_url": url,
            "from_listing_expansion": True,
            "access": access,
            "source_strategy": strat,
            "follow_detail_pages": follow,
        }
        children.append(
            CandidateURL(
                source_id=seed.source_id,
                company=seed.company,
                url=url,
                discovered_at=now,
                source_type=seed.source_type,
                hint_doc_type="article",
                priority=max(1, seed.priority - 5),
                metadata=child_meta,
            )
        )
    return children
