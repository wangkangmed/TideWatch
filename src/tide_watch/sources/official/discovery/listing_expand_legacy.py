"""纯链接启发式列表展开（无标题），供 listing_expand 回退使用。"""

from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse

from tide_watch.web.url_rules import canonicalize_url, is_allowed_url

_HREF_RE = re.compile(
    r"""<a\s+[^>]*href\s*=\s*(?P<q>['"])(?P<href>.*?)(?P=q)""",
    re.IGNORECASE | re.DOTALL,
)

_ARTICLE_PATH_HINTS = (
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
)


def _same_site(child: str, base: str) -> bool:
    try:
        a = urlparse(child)
        b = urlparse(base)
        if not a.netloc or not b.netloc:
            return False
        return a.netloc.lower() == b.netloc.lower()
    except Exception:
        return False


def _looks_like_article_url(listing_url: str, child_url: str) -> bool:
    lu = listing_url.rstrip("/").lower()
    cu = child_url.rstrip("/").lower()
    if cu == lu or cu.startswith(lu + "#"):
        return False
    path = urlparse(child_url).path.lower()
    if any(h in path for h in _ARTICLE_PATH_HINTS):
        return True
    lp = urlparse(listing_url).path.rstrip("/")
    if path.startswith(lp + "/") and len(path) > len(lp) + 1:
        tail = path[len(lp) + 1 :]
        if "/" in tail.strip("/"):
            return True
        if len(tail) > 12 and not tail.endswith((".xml", ".json", ".rss")):
            return True
    return False


def extract_article_links_from_listing_html(
    listing_url: str,
    html: str,
    *,
    max_links: int = 20,
) -> list[tuple[str, str | None]]:
    seen: set[str] = set()
    out: list[tuple[str, str | None]] = []
    for m in _HREF_RE.finditer(html or ""):
        raw = (m.group("href") or "").strip()
        if not raw or raw.startswith("#") or raw.lower().startswith("javascript:"):
            continue
        if raw.lower().startswith("mailto:"):
            continue
        abs_url = urljoin(listing_url, raw)
        abs_url = abs_url.split("#", 1)[0]
        if not is_allowed_url(abs_url):
            continue
        if not _same_site(abs_url, listing_url):
            continue
        if not _looks_like_article_url(listing_url, abs_url):
            continue
        can = canonicalize_url(abs_url)
        if can in seen:
            continue
        seen.add(can)
        out.append((can, None))
        if len(out) >= max_links:
            break
    return out
