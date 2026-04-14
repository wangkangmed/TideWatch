"""Heuristic origin guess: first_party/community/external_web."""

from __future__ import annotations

from urllib.parse import urlparse

from tide_watch.sources.search.models import SearchCandidate

_SOCIAL_DOMAINS = {
    "reddit.com",
    "www.reddit.com",
    "news.ycombinator.com",
    "x.com",
    "twitter.com",
    "linkedin.com",
    "www.linkedin.com",
    "youtube.com",
    "www.youtube.com",
}


def guess_origin_type(
    candidate: SearchCandidate,
    *,
    known_official_domains: set[str],
    social_domains: set[str] | None = None,
) -> SearchCandidate:
    domain = urlparse(candidate.canonical_url).netloc.lower() or candidate.domain
    community_domains = social_domains or _SOCIAL_DOMAINS
    if domain in known_official_domains:
        candidate.likely_origin_type = "first_party"
    elif domain in community_domains:
        candidate.likely_origin_type = "community"
    else:
        candidate.likely_origin_type = "external_web"
    candidate.metadata["origin_guess_domain"] = domain
    return candidate
