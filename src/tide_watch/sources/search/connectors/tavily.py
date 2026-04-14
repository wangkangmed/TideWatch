"""Tavily connector (API response mapping)."""

from __future__ import annotations

import os

import httpx

from tide_watch.sources.search.connectors.base import SearchConnector
from tide_watch.sources.search.models import SearchProviderConfig, SearchQuery, SearchResultItem


class TavilySearchConnector(SearchConnector):
    provider = "tavily"

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
        endpoint = provider_config.base_url or "https://api.tavily.com/search"
        payload = {
            "api_key": api_key,
            "query": query.text,
            "max_results": max(1, min(20, provider_config.default_limit)),
        }
        with httpx.Client(timeout=provider_config.timeout_sec) as client:
            resp = client.post(endpoint, json=payload)
            resp.raise_for_status()
            data = resp.json() or {}
        raw_items = data.get("results") or []
        out: list[SearchResultItem] = []
        for idx, row in enumerate(raw_items, start=1):
            url = str((row or {}).get("url") or "")
            if not url:
                continue
            out.append(
                SearchResultItem.with_domain(
                    query_id=query.query_id,
                    provider=provider_config.provider_id,
                    rank=idx,
                    url=url,
                    title=(row or {}).get("title"),
                    snippet=(row or {}).get("content"),
                    raw_metadata={"score": (row or {}).get("score")},
                )
            )
        return out
