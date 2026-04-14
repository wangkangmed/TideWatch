"""从列表 / 索引页 HTML 抽取条目级候选（链接 + 可选标题/摘要/日期）。"""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

from tide_watch.web.date_parser import parse_feed_date_string
from tide_watch.sources.official.source_definitions import SourceDefinition
from tide_watch.web.url_rules import canonicalize_url, is_allowed_url

# 通用“可能为详情页”的路径片段（可被子类 / YAML 追加）
_DEFAULT_PATH_HINTS: tuple[str, ...] = (
    "/news/",
    "/blog/",
    "/engineering/",
    "/research/",
    "/release",
    "/changelog",
    "/article/",
    "/posts/",
    "/stories/",
    "/updates/",
    "/product",
    "/papers/",
    "/publications/",
    "/discover/blog",
    "/science/blog",
    "/getting-started/changelog",
    "/release-notes",
    "/docs/en/release-notes",
)

_ANCHOR_RE = re.compile(
    r'<a\s+[^>]*href\s*=\s*(?P<q>[\'"])(?P<href>.*?)(?P=q)(?P<mid>[^>]*)>(?P<inner>.*?)</a>',
    re.IGNORECASE | re.DOTALL,
)
_TAG_STRIP = re.compile(r"<[^>]+>")


def _strip_html(s: str) -> str:
    t = _TAG_STRIP.sub(" ", s or "")
    t = re.sub(r"\s+", " ", t).strip()
    return t[:500] if len(t) > 500 else t


def _same_site(child: str, base: str) -> bool:
    try:
        a = urlparse(child)
        b = urlparse(base)
        if not a.netloc or not b.netloc:
            return False
        return a.netloc.lower() == b.netloc.lower()
    except Exception:
        return False


def _path_excluded(path: str, exclude: list[str]) -> bool:
    pl = path.lower()
    for sub in exclude:
        if sub.lower() in pl:
            return True
    return False


def _extra_hints(source: SourceDefinition | None) -> tuple[str, ...]:
    if not source or not source.listing_selectors:
        return ()
    raw = source.listing_selectors.get("path_contains_any") or []
    if isinstance(raw, list):
        return tuple(str(x) for x in raw)
    return ()


def _exclude_substrings(source: SourceDefinition | None) -> list[str]:
    if not source or not source.listing_selectors:
        return []
    raw = source.listing_selectors.get("exclude_path_substrings") or []
    if isinstance(raw, list):
        return [str(x) for x in raw]
    return []


def _looks_like_detail_url(listing_url: str, child_url: str, hints: tuple[str, ...]) -> bool:
    lu = listing_url.rstrip("/").lower()
    cu = child_url.rstrip("/").lower()
    if cu == lu or cu.startswith(lu + "#"):
        return False
    path = urlparse(child_url).path.lower()
    if any(h in path for h in hints):
        return True
    lp = urlparse(listing_url).path.rstrip("/")
    if path.startswith(lp + "/") and len(path) > len(lp) + 1:
        tail = path[len(lp) + 1 :].strip("/")
        if not tail or tail in ("page", "feed", "rss"):
            return False
        if "/" in tail:
            return True
        if len(tail) > 10 and not tail.endswith((".xml", ".json", ".rss", ".pdf")):
            return True
    return False


def _aggregate_like_url(url: str) -> bool:
    u = url.lower()
    noise = (
        "/content-type/",
        "/topic/",
        "/category/",
        "/tag/",
        "/page/",
        "/author/",
        "/industry/blog",
        "/blog/category/",
        "/blog/page",
    )
    return any(n in u for n in noise)


@dataclass
class ListingItemDraft:
    url: str
    title: str | None
    snippet: str | None
    published_at_hint: str | None


def extract_listing_item_drafts(
    listing_url: str,
    html: str,
    *,
    source: SourceDefinition | None = None,
    max_items: int = 24,
) -> list[ListingItemDraft]:
    """从 HTML 抽取条目草稿，供 expand 生成 CandidateURL。"""
    hints = _DEFAULT_PATH_HINTS + _extra_hints(source)
    exclude = _exclude_substrings(source)
    seen: set[str] = set()
    out: list[ListingItemDraft] = []

    for m in _ANCHOR_RE.finditer(html or ""):
        raw_href = (m.group("href") or "").strip()
        if not raw_href or raw_href.startswith("#") or raw_href.lower().startswith("javascript:"):
            continue
        if raw_href.lower().startswith("mailto:"):
            continue
        abs_url = urljoin(listing_url, raw_href).split("#", 1)[0]
        if not is_allowed_url(abs_url):
            continue
        if not _same_site(abs_url, listing_url):
            continue
        path = urlparse(abs_url).path
        if _path_excluded(path, exclude):
            continue
        if not _looks_like_detail_url(listing_url, abs_url, hints):
            continue
        if _aggregate_like_url(abs_url):
            allow = bool(source and (source.listing_selectors or {}).get("allow_aggregate_paths"))
            if not allow:
                continue
        can = canonicalize_url(abs_url)
        if can in seen:
            continue
        seen.add(can)
        title = _strip_html(m.group("inner") or "") or None
        if title and len(title) < 2:
            title = None
        out.append(ListingItemDraft(url=can, title=title, snippet=None, published_at_hint=None))
        if len(out) >= max_items:
            break

    return out


def draft_to_listing_metadata(draft: ListingItemDraft, listing_url: str) -> dict:
    pub = parse_feed_date_string(draft.published_at_hint) if draft.published_at_hint else None
    meta = {
        "discovery_method": "listing",
        "parent_listing_url": listing_url,
        "title": draft.title,
        "snippet": draft.snippet or "",
        "detail_url": draft.url,
    }
    if pub:
        meta["published_at"] = pub.isoformat()
    return meta
