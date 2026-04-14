"""Base abstraction for external search providers."""

from __future__ import annotations

from abc import ABC, abstractmethod

from tide_watch.sources.search.models import SearchProviderConfig, SearchQuery, SearchResultItem


class SearchConnector(ABC):
    provider: str

    @abstractmethod
    def search(
        self,
        query: SearchQuery,
        provider_config: SearchProviderConfig,
        *,
        checkpoint: dict | None = None,
    ) -> list[SearchResultItem]:
        """Execute provider search and map into SearchResultItem."""
