"""Routing decisions for fetch/reconcile/skip."""

from __future__ import annotations

from tide_watch.sources.search.models import RankedSearchCandidate, SearchCandidate
from tide_watch.sources.search.ranking.heuristics import score_candidate


def rank_and_route(
    candidates: list[SearchCandidate],
    *,
    time_window: str = "7d",
    min_fetch_score: float = 0.3,
) -> list[RankedSearchCandidate]:
    out: list[RankedSearchCandidate] = []
    for c in candidates:
        score, explain = score_candidate(c, time_window=time_window)
        c.score = score
        if score < min_fetch_score:
            route = "skip_low_value"
        elif c.likely_origin_type == "first_party":
            route = "route_to_official_reconcile"
        elif c.likely_origin_type == "community":
            route = "route_to_social_reconcile"
        else:
            route = "route_to_web_fetch"
        out.append(
            RankedSearchCandidate(
                candidate=c,
                route=route,
                explain=explain + [f"final_score={score:.3f}", f"route={route}"],
                fetch_priority=int(score * 100),
            )
        )
    out.sort(key=lambda x: x.fetch_priority, reverse=True)
    return out
