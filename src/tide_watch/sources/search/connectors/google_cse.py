"""Google CSE connector skeleton."""

from __future__ import annotations

from tide_watch.sources.search.connectors.base import SearchConnector
from tide_watch.sources.search.models import SearchProviderConfig, SearchQuery, SearchResultItem


class GoogleCseConnector(SearchConnector):
    provider = "google_cse"

    def search(
        self,
        query: SearchQuery,
        provider_config: SearchProviderConfig,
        *,
        checkpoint: dict | None = None,
    ) -> list[SearchResultItem]:
        _ = (query, provider_config, checkpoint)
        return []
