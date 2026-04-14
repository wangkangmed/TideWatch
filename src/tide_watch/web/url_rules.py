"""URL canonicalization and candidate scoring rules."""

from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

_TRACKING_KEYS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "gclid",
    "fbclid",
}


def canonicalize_url(url: str) -> str:
    p = urlparse(url.strip())
    q = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=False) if k not in _TRACKING_KEYS]
    q_sorted = urlencode(sorted(q))
    path = p.path.rstrip("/") or "/"
    return urlunparse((p.scheme.lower(), p.netloc.lower(), path, "", q_sorted, ""))


def score_candidate(url: str, source_priority: str = "medium") -> int:
    score = {"high": 90, "medium": 60, "low": 30}.get(source_priority, 50)
    lowered = url.lower()
    if "changelog" in lowered or "release" in lowered:
        score += 10
    if "news" in lowered or "blog" in lowered:
        score += 6
    return max(1, min(100, score))


def is_allowed_url(url: str) -> bool:
    lowered = url.lower()
    blocked_suffixes = (".jpg", ".png", ".gif", ".svg", ".pdf", ".zip")
    return not lowered.endswith(blocked_suffixes)
