"""Brave Search API connector."""

from __future__ import annotations

import os

import httpx

from tide_watch.sources.search.connectors.base import SearchConnector
from tide_watch.sources.search.models import SearchProviderConfig, SearchQuery, SearchResultItem


class BraveSearchConnector(SearchConnector):
    provider = "brave"

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
        endpoint = provider_config.base_url or "https://api.search.brave.com/res/v1/web/search"
        headers = {"X-Subscription-Token": api_key, "Accept": "application/json"}
        params: dict[str, str | int] = {
            "q": query.text,
            "count": max(1, min(20, provider_config.default_limit)),
        }
        country = (query.region or provider_config.region or "").strip()
        # Brave 对空字符串参数较敏感；仅在值有效时透传。
        if len(country) == 2 and country.isalpha():
            params["country"] = country.upper()
        lang = (query.language or provider_config.language or "").strip()
        if lang:
            params["search_lang"] = lang
        with httpx.Client(timeout=provider_config.timeout_sec) as client:
            resp = client.get(endpoint, params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json() or {}
        raw_items = ((data.get("web") or {}).get("results")) or []
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
                    snippet=(row or {}).get("description"),
                    raw_metadata={"age": (row or {}).get("age"), "profile": (row or {}).get("profile")},
                )
            )
        return out
