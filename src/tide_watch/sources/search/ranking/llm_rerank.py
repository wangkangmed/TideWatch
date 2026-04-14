"""Optional LLM rerank extension point; no-op by default."""

from __future__ import annotations

from tide_watch.sources.search.models import RankedSearchCandidate


def maybe_llm_rerank(items: list[RankedSearchCandidate], *, enabled: bool = False) -> list[RankedSearchCandidate]:
    if not enabled:
        return items
    return items
