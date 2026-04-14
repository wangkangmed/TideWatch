"""Search discovery pipeline: query -> provider -> merge -> guess -> route."""

from __future__ import annotations

import logging
from urllib.parse import urlparse

from tide_watch.sources.official.config_loader import load_source_config
from tide_watch.sources.search.config_loader import load_search_registry
from tide_watch.sources.search.connectors import connector_by_provider
from tide_watch.sources.search.enrichment.fetch_bridge import build_fetch_plans
from tide_watch.sources.search.models import RankedSearchCandidate, SearchResultItem
from tide_watch.sources.search.processing import guess_origin_type, merge_results_to_candidates, rank_and_route
from tide_watch.sources.search.query import build_queries_for_monitor
from tide_watch.sources.search.registry import SearchRegistry

logger = logging.getLogger(__name__)


def _collect_official_domains(config_path: str | None) -> set[str]:
    cfg = load_source_config(config_path)
    out: set[str] = set()
    for comp in cfg.companies:
        for src in comp.sources:
            host = urlparse(src.url).netloc.lower()
            if host:
                out.add(host)
            if src.rss_url:
                host = urlparse(src.rss_url).netloc.lower()
                if host:
                    out.add(host)
            if src.sitemap_url:
                host = urlparse(src.sitemap_url).netloc.lower()
                if host:
                    out.add(host)
    return out


def run_search_discovery(
    *,
    config_path: str | None = None,
    top_n: int = 30,
    min_fetch_score: float = 0.3,
) -> tuple[list[RankedSearchCandidate], list[SearchResultItem]]:
    search_cfg = load_search_registry(config_path)
    registry = SearchRegistry(search_cfg)
    official_domains = _collect_official_domains(config_path)
    all_results: list[SearchResultItem] = []

    for monitor in registry.iter_enabled_monitors():
        queries = build_queries_for_monitor(monitor, expand=False)
        provider_ids = monitor.providers or [p.provider_id for p in registry.iter_enabled_providers()]
        for provider_id in provider_ids:
            try:
                pconf = registry.provider(provider_id)
            except KeyError:
                logger.warning("search provider missing provider_id=%s monitor=%s", provider_id, monitor.monitor_id)
                continue
            if not pconf.enabled:
                continue
            connector = connector_by_provider(pconf.provider)
            for q in queries:
                try:
                    all_results.extend(connector.search(q, pconf))
                except Exception as exc:  # noqa: BLE001
                    logger.warning(
                        "search provider failed monitor=%s provider=%s query=%s err=%s",
                        monitor.monitor_id,
                        pconf.provider_id,
                        q.query_id,
                        exc,
                    )

    candidates = merge_results_to_candidates(all_results)
    for c in candidates:
        guess_origin_type(c, known_official_domains=official_domains)
    ranked = rank_and_route(candidates, min_fetch_score=min_fetch_score)
    return ranked[:top_n], all_results


def run_search_discovery_with_fetch_plans(
    *,
    config_path: str | None = None,
    top_n: int = 30,
    min_fetch_score: float = 0.3,
):
    ranked, results = run_search_discovery(config_path=config_path, top_n=top_n, min_fetch_score=min_fetch_score)
    return ranked, results, build_fetch_plans(ranked)
