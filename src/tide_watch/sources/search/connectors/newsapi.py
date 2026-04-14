"""NewsAPI connector: suitable for trend/news freshness discovery."""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any

import httpx

from tide_watch.sources.search.connectors.base import SearchConnector
from tide_watch.sources.search.models import SearchProviderConfig, SearchQuery, SearchResultItem


class NewsApiConnector(SearchConnector):
    provider = "newsapi"

    def search(
        self,
        query: SearchQuery,
        provider_config: SearchProviderConfig,
        *,
        checkpoint: dict | None = None,
    ) -> list[SearchResultItem]:
        api_key = os.getenv(provider_config.api_key_ref or "")
        if not api_key:
            return []
        endpoint = provider_config.base_url or "https://newsapi.org/v2/everything"
        params = {
            "q": query.text,
            "language": query.language or provider_config.language,
            "pageSize": max(1, min(100, provider_config.default_limit)),
            "sortBy": "publishedAt",
        }
        if query.metadata.get("monitor_topic"):
            params["searchIn"] = "title,description"
        headers = {"X-Api-Key": api_key}
        with httpx.Client(timeout=provider_config.timeout_sec) as client:
            resp = client.get(endpoint, params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json() or {}
        items = data.get("articles") or []
        out: list[SearchResultItem] = []
        for idx, row in enumerate(items, start=1):
            url = str((row or {}).get("url") or "")
            if not url:
                continue
            published_hint = None
            pub_raw = (row or {}).get("publishedAt")
            if isinstance(pub_raw, str) and pub_raw:
                try:
                    published_hint = datetime.fromisoformat(pub_raw.replace("Z", "+00:00"))
                except ValueError:
                    published_hint = None
            out.append(
                SearchResultItem.with_domain(
                    query_id=query.query_id,
                    provider=provider_config.provider_id,
                    rank=idx,
                    url=url,
                    title=(row or {}).get("title"),
                    snippet=(row or {}).get("description"),
                    published_hint=published_hint,
                    raw_metadata={
                        "source": (row or {}).get("source"),
                        "author": (row or {}).get("author"),
                        "content": (row or {}).get("content"),
                    },
                )
            )
        return out
