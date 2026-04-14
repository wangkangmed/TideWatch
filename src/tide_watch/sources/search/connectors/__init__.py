from tide_watch.sources.search.connectors.base import SearchConnector
from tide_watch.sources.search.connectors.brave import BraveSearchConnector
from tide_watch.sources.search.connectors.exa import ExaSearchConnector
from tide_watch.sources.search.connectors.google_cse import GoogleCseConnector
from tide_watch.sources.search.connectors.newsapi import NewsApiConnector
from tide_watch.sources.search.connectors.tavily import TavilySearchConnector


def connector_by_provider(provider: str) -> SearchConnector:
    key = (provider or "").strip().lower()
    if key == "newsapi":
        return NewsApiConnector()
    if key == "brave":
        return BraveSearchConnector()
    if key == "tavily":
        return TavilySearchConnector()
    if key == "exa":
        return ExaSearchConnector()
    if key == "google_cse":
        return GoogleCseConnector()
    raise KeyError(f"unknown search provider: {provider}")


__all__ = [
    "SearchConnector",
    "NewsApiConnector",
    "BraveSearchConnector",
    "TavilySearchConnector",
    "ExaSearchConnector",
    "GoogleCseConnector",
    "connector_by_provider",
]
