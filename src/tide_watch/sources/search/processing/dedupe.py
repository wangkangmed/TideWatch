"""Dedupe + merge search results into unified candidates."""

from __future__ import annotations

import hashlib
from typing import Iterable
from urllib.parse import urlparse

from tide_watch.sources.search.models import SearchCandidate, SearchResultItem
from tide_watch.web.url_rules import canonicalize_url


def merge_results_to_candidates(results: Iterable[SearchResultItem]) -> list[SearchCandidate]:
    merged: dict[str, SearchCandidate] = {}
    for item in results:
        canonical = canonicalize_url(item.url)
        if canonical not in merged:
            cid = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:20]
            merged[canonical] = SearchCandidate(
                candidate_id=f"search:{cid}",
                url=item.url,
                canonical_url=canonical,
                title_hint=item.title,
                summary_hint=item.snippet,
                published_hint=item.published_hint,
                domain=urlparse(canonical).netloc.lower(),
                matched_queries=[item.query_id],
                discovery_channels=["web_search"],
                provider_hits=[item.provider],
                metadata={
                    "provider_evidence": [
                        {
                            "provider": item.provider,
                            "rank": item.rank,
                            "title": item.title,
                            "snippet": item.snippet,
                        }
                    ]
                },
            )
            continue
        cur = merged[canonical]
        if item.query_id not in cur.matched_queries:
            cur.matched_queries.append(item.query_id)
        if item.provider not in cur.provider_hits:
            cur.provider_hits.append(item.provider)
        if item.published_hint and (not cur.published_hint or item.published_hint > cur.published_hint):
            cur.published_hint = item.published_hint
        evidence = cur.metadata.setdefault("provider_evidence", [])
        if isinstance(evidence, list):
            evidence.append(
                {
                    "provider": item.provider,
                    "rank": item.rank,
                    "title": item.title,
                    "snippet": item.snippet,
                }
            )
    return list(merged.values())
