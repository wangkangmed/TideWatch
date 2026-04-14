"""页面类型判定：正文页 vs 列表/聚合/文档壳 / 挑战页。"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Literal

from tide_watch.web.block_classifier import is_challenge_block
from tide_watch.models.ingestion import BlockType

PageType = Literal[
    "article_page",
    "listing_page",
    "aggregation_page",
    "docs_shell_page",
    "challenge_or_interstitial",
]

_SCRIPT_JSONLD = re.compile(
    r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.I | re.DOTALL,
)

_CHALLENGE_SNIPPETS = (
    "just a moment",
    "attention required",
    "checking your browser",
    "cf-chl",
    "challenge-platform",
)
_HREF_RE = re.compile(r"\bhref\s*=", re.I)
_OG_TYPE_RE = re.compile(
    r'<meta[^>]+property=["\']og:type["\'][^>]+content=["\']([^"\']+)["\']',
    re.I,
)
_ARTICLE_TAG = re.compile(r"<article[\s>]", re.I)
_MAIN_TAG = re.compile(r"<main[\s>]", re.I)
_ROLE_MAIN = re.compile(r'role=["\']main["\']', re.I)
_CARD_CLASS = re.compile(
    r"class=[\"'][^\"']*(?:card|teaser|tile|grid-item|post-preview|story-card)[^\"']*[\"']",
    re.I,
)
_AGG_URL_PARTS = (
    "/content-type/",
    "/topic/",
    "/category/",
    "/tag/",
    "/property/",
    "/industry/",
    "/blog/category/",
    "/blog/page/",
    "/author/",
)
_FEATURED_OR_NAV_TITLE = re.compile(
    r"^\s*(featured|learn more|read more|blog|news|updates|archives)\s*$",
    re.I,
)


def _clean_len(s: str) -> int:
    return len(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s or "")).strip())


def _link_count(html: str) -> int:
    return len(_HREF_RE.findall(html or ""))


def _collect_jsonld_types(html: str) -> list[str]:
    out: list[str] = []

    def walk(obj: Any) -> None:
        if isinstance(obj, dict):
            t = obj.get("@type")
            if isinstance(t, str):
                out.append(t.lower())
            elif isinstance(t, list):
                out.extend(str(x).lower() for x in t)
            for v in obj.values():
                walk(v)
        elif isinstance(obj, list):
            for item in obj:
                walk(item)

    for m in _SCRIPT_JSONLD.finditer(html or ""):
        blob = re.sub(r"<[^>]+>", " ", m.group(1) or "").strip()
        if not blob:
            continue
        try:
            data = json.loads(blob)
        except json.JSONDecodeError:
            continue
        walk(data)
    return out


@dataclass
class PageClassification:
    page_type: PageType
    page_signals: dict[str, Any] = field(default_factory=dict)
    """建议正文处理方式：full 保留去标签全文；trimmed 截断；metadata_only 仅用摘要/元数据。"""
    body_handling: Literal["full", "trimmed", "metadata_only"] = "full"
    quality_cap: float = 0.85
    suggested_snippet: str | None = None


def classify_html_page(
    html: str,
    url: str,
    *,
    title: str | None = None,
    block_type: BlockType = "success",
    meta_description: str | None = None,
) -> PageClassification:
    """
    不单独依赖正文长度；结合 URL、DOM 信号、og:type、JSON-LD、链接密度等。
    """
    h = html or ""
    low = h.lower()
    u = (url or "").lower()
    signals: dict[str, Any] = {}

    if is_challenge_block(block_type):
        return PageClassification(
            page_type="challenge_or_interstitial",
            page_signals={"reason": "block_type_challenge"},
            body_handling="metadata_only",
            quality_cap=0.12,
            suggested_snippet=meta_description,
        )
    if len(low) > 200 and any(p in low for p in _CHALLENGE_SNIPPETS):
        return PageClassification(
            page_type="challenge_or_interstitial",
            page_signals={"reason": "challenge_body_patterns"},
            body_handling="metadata_only",
            quality_cap=0.12,
            suggested_snippet=meta_description,
        )

    text_len = _clean_len(h)
    links = _link_count(h)
    signals["link_count"] = links
    signals["approx_text_len"] = text_len
    signals["has_article"] = bool(_ARTICLE_TAG.search(h))
    signals["has_main"] = bool(_MAIN_TAG.search(h) or _ROLE_MAIN.search(h))
    card_hits = len(_CARD_CLASS.findall(h))
    signals["card_class_hits"] = card_hits
    ld_types = _collect_jsonld_types(h)
    signals["json_ld_types"] = ld_types[:12]
    article_like_ld = any(
        t in ("newsarticle", "article", "blogposting", "blogpostings", "techarticle") for t in ld_types
    )
    signals["json_ld_article_like"] = article_like_ld

    m = _OG_TYPE_RE.search(h)
    og_type = (m.group(1) or "").lower() if m else ""
    signals["og_type"] = og_type or None

    link_density = links / max(text_len, 1) * 1000  # links per 1k visible chars
    signals["link_density_per_1k_chars"] = round(link_density, 3)

    if article_like_ld and link_density < 10 and not any(seg in u for seg in _AGG_URL_PARTS):
        return PageClassification(
            page_type="article_page",
            page_signals=signals,
            body_handling="full",
            quality_cap=0.8,
            suggested_snippet=meta_description,
        )

    if any(seg in u for seg in _AGG_URL_PARTS):
        signals["aggregation_url_match"] = True
        snip = meta_description or (title or "")[:400]
        return PageClassification(
            page_type="aggregation_page",
            page_signals=signals,
            body_handling="trimmed",
            quality_cap=0.28,
            suggested_snippet=snip,
        )

    if og_type in ("website", "profile"):
        snip = meta_description or (title or "")[:400]
        return PageClassification(
            page_type="listing_page",
            page_signals=signals,
            body_handling="trimmed",
            quality_cap=0.32,
            suggested_snippet=snip,
        )

    if og_type in ("article", "newsarticle", "blogpostings"):
        signals["og_article_like"] = True
        return PageClassification(
            page_type="article_page",
            page_signals=signals,
            body_handling="full",
            quality_cap=0.82,
            suggested_snippet=meta_description,
        )

    # 高链接密度 + 多卡片 → 聚合/列表
    if link_density > 8 and (card_hits >= 6 or links > 80):
        snip = meta_description or (title or "")[:400]
        return PageClassification(
            page_type="aggregation_page",
            page_signals=signals,
            body_handling="trimmed",
            quality_cap=0.26,
            suggested_snippet=snip,
        )

    if signals["has_article"] or signals["has_main"]:
        if link_density > 12 and not og_type:
            snip = meta_description or (title or "")[:400]
            return PageClassification(
                page_type="listing_page",
                page_signals=signals,
                body_handling="trimmed",
                quality_cap=0.35,
                suggested_snippet=snip,
            )
        return PageClassification(
            page_type="article_page",
            page_signals=signals,
            body_handling="full",
            quality_cap=0.78,
            suggested_snippet=meta_description,
        )

    # Next / docs 壳：大量 script、可见文本少
    script_weight = len(re.findall(r"<script[^>]*>", h, re.I))
    signals["script_tag_count"] = script_weight
    if script_weight > 40 and text_len < 2500:
        snip = meta_description or (title or "")[:400]
        return PageClassification(
            page_type="docs_shell_page",
            page_signals=signals,
            body_handling="trimmed",
            quality_cap=0.3,
            suggested_snippet=snip,
        )

    if title and _FEATURED_OR_NAV_TITLE.match(title.strip()):
        return PageClassification(
            page_type="listing_page",
            page_signals=signals,
            body_handling="trimmed",
            quality_cap=0.22,
            suggested_snippet=meta_description,
        )

    # 默认：偏文章但保守
    if text_len > 800 and link_density < 6:
        return PageClassification(
            page_type="article_page",
            page_signals=signals,
            body_handling="full",
            quality_cap=0.65,
            suggested_snippet=meta_description,
        )

    snip = meta_description or (title or "")[:400]
    return PageClassification(
        page_type="listing_page",
        page_signals=signals,
        body_handling="trimmed",
        quality_cap=0.38,
        suggested_snippet=snip,
    )
