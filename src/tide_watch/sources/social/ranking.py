"""轻量 engagement / quality 评分，平台无关入口 + 可扩展启发式。"""

from __future__ import annotations

import re
from typing import Any

from tide_watch.sources.social.models import SocialCandidateItem

_URL_RE = re.compile(r"https?://", re.I)


def engagement_score_from_signals(engagement: dict[str, Any], platform: str) -> float:
    """把各平台 engagement 字典压成单一分数，便于排序。"""
    if platform == "reddit":
        s = float(engagement.get("score") or 0)
        c = float(engagement.get("num_comments") or 0)
        return min(1.0, (s**0.5) / 200.0 + (c**0.5) / 150.0)
    if platform == "hackernews":
        s = float(engagement.get("points") or 0)
        c = float(engagement.get("num_comments") or 0)
        return min(1.0, (s**0.5) / 180.0 + (c**0.5) / 120.0)
    if platform == "x":
        for k in ("like_count", "retweet_count", "reply_count", "quote_count"):
            if k in engagement:
                return min(1.0, float(engagement.get(k) or 0) / 5000.0)
        return 0.0
    base = float(engagement.get("score") or engagement.get("votes") or 0)
    return min(1.0, base / 500.0)


def trust_weight(trust_tier: int) -> float:
    """trust_tier 越大表示越可信（与业务约定一致）。"""
    return max(0.1, min(1.0, float(trust_tier) / 5.0))


def looks_like_noise(text: str, title: str | None) -> bool:
    """极简噪声启发：极短正文、纯导航式标题。"""
    blob = f"{title or ''} {text}".strip()
    if len(blob) < 12:
        return True
    low = blob.lower()
    if low in {"discussion", "ask hn", "[deleted]", "[removed]"}:
        return True
    if title and len(title) < 6 and len(text) < 40:
        return True
    return False


def has_outbound_links(text: str) -> bool:
    return bool(_URL_RE.search(text or ""))


def compute_quality_score(
    item: SocialCandidateItem,
    *,
    content_text: str,
    trust_tier: int,
    has_comment_context: bool,
    metadata_only: bool,
) -> float:
    """综合质量分： engagement + 可信度 + 上下文完整性 + 噪声惩罚。"""
    eng = engagement_score_from_signals(item.engagement, item.platform)
    tw = trust_weight(trust_tier)
    ctx = 0.15 if has_comment_context else 0.0
    link_bonus = 0.05 if has_outbound_links(content_text) else 0.0
    noise_penalty = 0.25 if looks_like_noise(content_text, item.title) else 0.0
    meta_penalty = 0.2 if metadata_only else 0.0
    raw = eng * tw + ctx + link_bonus - noise_penalty - meta_penalty
    return max(0.0, min(1.0, raw))
