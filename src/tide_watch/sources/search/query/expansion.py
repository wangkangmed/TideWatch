"""Optional query expansion hook (LLM or rules), disabled by default."""

from __future__ import annotations

from tide_watch.sources.search.models import SearchQuery


def expand_queries(queries: list[SearchQuery], *, enabled: bool = False) -> list[SearchQuery]:
    if not enabled:
        return queries
    return queries
