"""Compatibility exports for search discovery layer."""

from tide_watch.sources.search.models import SearchCandidate, SearchQuery, SearchResultItem
from tide_watch.sources.search.pipeline import run_search_discovery

__all__ = ["SearchQuery", "SearchResultItem", "SearchCandidate", "run_search_discovery"]
