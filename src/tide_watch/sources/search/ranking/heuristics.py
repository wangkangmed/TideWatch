"""Explainable heuristic ranking for search candidates."""

from __future__ import annotations

from datetime import datetime, timezone

from tide_watch.sources.search.models import SearchCandidate, parse_time_window_to_cutoff


def score_candidate(candidate: SearchCandidate, *, time_window: str = "7d") -> tuple[float, list[str]]:
    explain: list[str] = []
    score = 0.0

    query_hits = len(candidate.matched_queries)
    provider_hits = len(candidate.provider_hits)
    score += min(0.35, query_hits * 0.1)
    score += min(0.25, provider_hits * 0.08)
    explain.append(f"query_hits={query_hits}")
    explain.append(f"provider_hits={provider_hits}")

    if candidate.published_hint:
        cutoff = parse_time_window_to_cutoff(time_window, now=datetime.now(timezone.utc))
        if cutoff and candidate.published_hint >= cutoff:
            score += 0.2
            explain.append("freshness=within_window")
        else:
            explain.append("freshness=stale_or_unknown")
    else:
        explain.append("freshness=missing")

    if candidate.likely_origin_type == "first_party":
        score += 0.15
        explain.append("origin=first_party_bonus")
    elif candidate.likely_origin_type == "community":
        score += 0.1
        explain.append("origin=community_bonus")
    else:
        explain.append("origin=external_web")

    if candidate.title_hint and len(candidate.title_hint) > 10:
        score += 0.05
        explain.append("title_signal=good")

    return max(0.0, min(1.0, score)), explain
