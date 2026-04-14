"""Official 采集：多 transport discovery +（enrichment 由 LangGraph 子图承担）。"""

from __future__ import annotations

import logging
from typing import Any, Literal

from tide_watch.sources.official.discovery import (
    discover_from_listing,
    discover_from_rest_api,
    discover_from_rss,
    discover_from_sitemap,
)
from tide_watch.sources.official.registry import SourceRegistry
from tide_watch.sources.official.source_definitions import (
    CandidateURL,
    OfficialTransportConfig,
    SourceDefinition,
    SourceRegistryConfig,
)
from tide_watch.web.url_rules import score_candidate

logger = logging.getLogger(__name__)
CollectionMode = Literal["balanced", "rss_first", "rss_only"]


def resolved_transport_strategies(source: SourceDefinition) -> list[OfficialTransportConfig]:
    if source.strategies:
        return [s for s in source.strategies if s.enabled]
    legacy: list[OfficialTransportConfig] = []
    st = source.type.lower()
    if source.rss_url:
        legacy.append(OfficialTransportConfig(transport="rss", url=source.rss_url, priority=100))
    if source.sitemap_url:
        legacy.append(OfficialTransportConfig(transport="sitemap", url=source.sitemap_url, priority=80))
    if source.api_list_url:
        legacy.append(
            OfficialTransportConfig(
                transport="rest_api",
                url=source.api_list_url,
                priority=120,
                headers=dict(source.api_headers or {}),
                items_path=source.api_items_path,
                field_map=dict(source.api_field_map or {}),
            )
        )
    if "rss" in st or st in {"atom", "feed"}:
        legacy.append(OfficialTransportConfig(transport="rss", url=source.url, priority=90))
    elif "sitemap" in st:
        legacy.append(OfficialTransportConfig(transport="sitemap", url=source.url, priority=90))
    else:
        legacy.append(OfficialTransportConfig(transport="html_listing", url=source.url, priority=60))
    return [x for x in legacy if x.enabled]


def _run_single_transport(
    company: str,
    source: SourceDefinition,
    strat: OfficialTransportConfig,
    per_cap: int,
) -> list[CandidateURL]:
    if strat.transport == "rss":
        return discover_from_rss(company, source, max_items=per_cap, feed_url=strat.url)
    if strat.transport == "sitemap":
        return discover_from_sitemap(company, source, max_items=per_cap, sitemap_url=strat.url)
    if strat.transport == "html_listing":
        return discover_from_listing(company, source, listing_url=strat.url)
    if strat.transport == "rest_api":
        return discover_from_rest_api(company, source, strat, max_items=per_cap)
    return []


def _apply_collection_mode(
    source: SourceDefinition,
    strategies: list[OfficialTransportConfig],
    mode: CollectionMode,
) -> list[OfficialTransportConfig]:
    if mode == "rss_only":
        return [s for s in strategies if s.transport == "rss"]
    if mode == "rss_first":
        return sorted(strategies, key=lambda s: (0 if s.transport == "rss" else 1, -s.priority))
    return sorted(strategies, key=lambda s: -s.priority)


def collect_official_discovery_with_report(
    cfg: SourceRegistryConfig,
    *,
    max_candidates: int = 200,
    collection_mode: CollectionMode = "balanced",
) -> tuple[list[CandidateURL], dict[str, Any]]:
    """Discovery + transport-level error report.

    Report schema:
    {
      "by_source": {"source_id": {"attempted": int, "succeeded": int, "errors": [str, ...]}},
      "summary": {"attempted": int, "succeeded": int, "errors": int},
    }
    """
    """按 source 解析 transports，支持 combine / prefer_fallback，输出 CandidateURL。"""
    reg = SourceRegistry(cfg)
    out: list[CandidateURL] = []
    by_source: dict[str, dict[str, Any]] = {}
    attempted = succeeded = err_cnt = 0
    for _sid, company, source in reg.iter_sources():
        if not source.enabled:
            continue
        strategies = _apply_collection_mode(source, resolved_transport_strategies(source), collection_mode)
        if not strategies:
            continue
        src_stat = by_source.setdefault(source.id, {"attempted": 0, "succeeded": 0, "errors": []})
        per_cap = max(8, max_candidates // max(1, len(strategies)))
        if source.transport_collection_mode == "prefer_fallback":
            chunk: list[CandidateURL] = []
            for st in strategies:
                attempted += 1
                src_stat["attempted"] += 1
                try:
                    chunk = _run_single_transport(company, source, st, per_cap)
                    if chunk:
                        succeeded += 1
                        src_stat["succeeded"] += 1
                        break
                except Exception as exc:  # noqa: BLE001
                    err_cnt += 1
                    msg = f"{st.transport}: {exc!s}"
                    src_stat["errors"].append(msg)
                    logger.warning(
                        "discover_transport_failed source=%s company=%s transport=%s err=%s",
                        source.id,
                        company,
                        st.transport,
                        exc,
                    )
            discovered = chunk
        else:
            merged: list[CandidateURL] = []
            seen: set[str] = set()
            for st in strategies:
                attempted += 1
                src_stat["attempted"] += 1
                try:
                    chunk = _run_single_transport(company, source, st, per_cap)
                    if chunk:
                        succeeded += 1
                        src_stat["succeeded"] += 1
                    for c in chunk:
                        if c.url in seen:
                            continue
                        seen.add(c.url)
                        c.metadata.setdefault("transport", st.transport)
                        merged.append(c)
                except Exception as exc:  # noqa: BLE001
                    err_cnt += 1
                    msg = f"{st.transport}: {exc!s}"
                    src_stat["errors"].append(msg)
                    logger.warning(
                        "discover_transport_failed source=%s company=%s transport=%s err=%s",
                        source.id,
                        company,
                        st.transport,
                        exc,
                    )
            discovered = merged[: max_candidates]
        for c in discovered:
            c.priority = score_candidate(c.url, source.priority)
            c.metadata["access"] = source.access
        out.extend(discovered)
    out = sorted(out, key=lambda x: x.priority, reverse=True)[:max_candidates]
    report = {
        "by_source": by_source,
        "summary": {"attempted": attempted, "succeeded": succeeded, "errors": err_cnt},
    }
    return out, report


def collect_official_discovery(
    cfg: SourceRegistryConfig,
    *,
    max_candidates: int = 200,
    collection_mode: CollectionMode = "balanced",
) -> list[CandidateURL]:
    items, _report = collect_official_discovery_with_report(
        cfg,
        max_candidates=max_candidates,
        collection_mode=collection_mode,
    )
    return items


def collect_official_enrichment(state: dict[str, Any]) -> dict[str, Any]:
    """占位说明：正文抽取 / structured_index / metadata fallback 由 ``build_ingestion_subgraph`` 后续节点完成。"""
    return state
