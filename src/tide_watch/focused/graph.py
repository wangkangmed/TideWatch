"""LangGraph content ingestion subgraph."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from langgraph.graph import END, START, StateGraph

from tide_watch.web.block_classifier import classify_fetch_result, is_challenge_block
from tide_watch.web.deduper import dedup_documents
from tide_watch.web.extractors import (
    extract_document,
    extract_listing_index_fallback,
    metadata_rich_document,
)
from tide_watch.web.http_client import run_fetch_plan
from tide_watch.web.normalizers import normalize_document
from tide_watch.web.url_rules import canonicalize_url, is_allowed_url
from tide_watch.models.ingestion import FetchAttempt, IngestionRunStats, SourceHealth
from tide_watch.sources.official.config_loader import load_source_config
from tide_watch.sources.official.enrichment.listing_expand import expand_listing_seed
from tide_watch.sources.official.enrichment.structured_index import extract_structured_index_document
from tide_watch.sources.official.enrichment.fetch_strategy import decide_access_plan
from tide_watch.sources.official.health import merge_health_from_normalized_doc, update_health
from tide_watch.sources.official.persistence import IngestionRepository
from tide_watch.config.settings import TideWatchSettings
from tide_watch.sources.official.pipeline import collect_official_discovery_with_report
from tide_watch.sources.official.source_definitions import CandidateURL
from tide_watch.sources.official.strategies.source_strategy import source_def_from_config_dict
from tide_watch.focused.state import IngestionState

logger = logging.getLogger(__name__)


def _discover_candidates(state: IngestionState) -> dict[str, Any]:
    cfg = load_source_config(state.get("source_config_path"))
    max_candidates = int(state.get("max_candidates") or 200)
    settings = TideWatchSettings()
    try:
        candidates, report = collect_official_discovery_with_report(
            cfg,
            max_candidates=max_candidates,
            collection_mode=str(settings.official_collection_mode or "balanced"),  # balanced|rss_first|rss_only
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("collect_official_discovery_failed err=%s", exc)
        candidates = []
        report = {"summary": {"attempted": 0, "succeeded": 0, "errors": 1}, "by_source": {}}
    stats = IngestionRunStats(discovered=len(candidates))
    errs = []
    for sid, row in (report.get("by_source") or {}).items():
        for e in row.get("errors") or []:
            errs.append(f"{sid}:{e}")
    return {
        "source_config": cfg.model_dump(),
        "candidates": candidates,
        "stats": stats,
        "errors": errs,
        "discovery_report": report,
    }


def _canonicalize_candidates(state: IngestionState) -> dict[str, Any]:
    seen: set[str] = set()
    out: list[CandidateURL] = []
    for cand in state.get("candidates") or []:
        if not is_allowed_url(cand.url):
            continue
        can = canonicalize_url(cand.url)
        if can in seen:
            continue
        seen.add(can)
        cand.url = can
        out.append(cand)
    return {"canonical_candidates": out}


def _expand_listing_two_level(state: IngestionState) -> dict[str, Any]:
    """第一级：列表种子 URL；第二级：同页抽取文章链接后再进入 fetch。"""
    seeds = state.get("canonical_candidates") or []
    max_per = int(state.get("listing_max_child_links") or 15)
    global_max = int(state.get("max_candidates") or 200)
    expanded: list[CandidateURL] = []
    for cand in seeds:
        is_seed = bool(cand.metadata.get("seed")) or cand.hint_doc_type == "listing"
        if not is_seed:
            expanded.append(cand)
            continue
        src = source_def_from_config_dict(state.get("source_config"), cand.source_id)
        children = expand_listing_seed(cand, source=src, max_child_links=max_per)
        if children:
            expanded.extend(children)
        else:
            expanded.append(cand)
    seen: set[str] = set()
    merged: list[CandidateURL] = []
    for c in sorted(expanded, key=lambda x: -x.priority):
        if c.url in seen:
            continue
        seen.add(c.url)
        merged.append(c)
    merged = merged[:global_max]
    logger.info(
        "listing_two_level expanded seeds=%s out_candidates=%s",
        len(seeds),
        len(merged),
    )
    return {"canonical_candidates": merged}


def _decide_access_strategy(state: IngestionState) -> dict[str, Any]:
    health_map = dict(state.get("source_health") or {})
    plans = []
    for cand in state.get("canonical_candidates") or []:
        plans.append(decide_access_plan(cand, health_map.get(cand.source_id)))
    return {"fetch_plans": plans}


def _fetch_and_classify(state: IngestionState) -> dict[str, Any]:
    results = []
    attempts = []
    for plan in state.get("fetch_plans") or []:
        result = classify_fetch_result(run_fetch_plan(plan))
        result.discovered_metadata = dict(result.discovered_metadata or {})
        result.discovered_metadata["plan_reason"] = plan.reason
        result.discovered_metadata["requested_mode"] = plan.mode
        if is_challenge_block(result.detected_block_type):
            # Hard requirement: do not bypass challenge, degrade immediately.
            result.fetch_mode = "metadata_only"
        results.append(result)
        attempts.append(
            FetchAttempt(
                source_id=result.source_id,
                url=result.url,
                status_code=result.status_code,
                block_type=result.detected_block_type,
                fetch_mode=result.fetch_mode,
                retryable=result.retryable,
                error=result.error,
                created_at=datetime.now(timezone.utc),
            )
        )
    return {"fetch_results": results, "fetch_attempts": attempts}


def _extract_documents(state: IngestionState) -> dict[str, Any]:
    candidate_by_url = {c.url: c for c in state.get("canonical_candidates") or []}
    out = []
    for result in state.get("fetch_results") or []:
        cand = candidate_by_url.get(result.url)
        if cand is None:
            continue
        meta = cand.metadata or {}
        mode = result.fetch_mode
        has_body = bool((result.raw_html or result.raw_text or "").strip())

        strat = meta.get("source_strategy") or ""

        if mode in {"feed_only", "skip"}:
            out.append(metadata_rich_document(cand, result))
            continue
        if mode == "metadata_only":
            if strat == "structured_index" and has_body:
                out.append(extract_structured_index_document(cand, result))
            else:
                out.append(metadata_rich_document(cand, result))
            continue
        if mode == "listing_only":
            if result.success and has_body and (meta.get("seed") or cand.hint_doc_type == "listing"):
                if strat == "structured_index":
                    out.append(extract_structured_index_document(cand, result))
                else:
                    out.append(extract_listing_index_fallback(cand, result))
            else:
                out.append(metadata_rich_document(cand, result))
            continue
        if not has_body:
            out.append(metadata_rich_document(cand, result))
            continue
        if strat == "structured_index":
            out.append(extract_structured_index_document(cand, result))
            continue
        out.append(extract_document(cand, result))
    return {"extracted_docs": out}


def _normalize_documents(state: IngestionState) -> dict[str, Any]:
    result_by_url = {r.url: r for r in state.get("fetch_results") or []}
    cand_by_url = {c.url: c for c in state.get("canonical_candidates") or []}
    docs = []
    for ex in state.get("extracted_docs") or []:
        cand = cand_by_url.get(ex.url)
        result = result_by_url.get(ex.url)
        if cand is None or result is None:
            continue
        docs.append(
            normalize_document(
                ex,
                result,
                source_type=cand.source_type,
                doc_type_hint=cand.hint_doc_type,
            )
        )
    stats = state.get("stats") or IngestionRunStats()
    stats.fetched = len(state.get("fetch_results") or [])
    stats.normalized = len(docs)
    return {"normalized_docs": docs, "stats": stats}


def _dedup_documents(state: IngestionState) -> dict[str, Any]:
    deduped = dedup_documents(state.get("normalized_docs") or [])
    stats = state.get("stats") or IngestionRunStats()
    stats.deduped = len(deduped)
    return {"deduped_docs": deduped, "stats": stats}


def _persist_documents(state: IngestionState) -> dict[str, Any]:
    repo = IngestionRepository()
    persisted_ids = []
    for item in state.get("deduped_docs") or []:
        repo.save_doc(item)
        persisted_ids.append(item.document_id)
    for att in state.get("fetch_attempts") or []:
        repo.save_attempt(att)
    return {"persisted_docs": persisted_ids}


def _update_source_health(state: IngestionState) -> dict[str, Any]:
    repo = IngestionRepository()
    health = repo.load_health()
    for result in state.get("fetch_results") or []:
        health[result.source_id] = update_health(health.get(result.source_id), result)
    for doc in state.get("deduped_docs") or []:
        sid = doc.source_id
        health[sid] = merge_health_from_normalized_doc(health.get(sid), doc)
    repo.save_health(health)
    return {"source_health": health}


def build_ingestion_subgraph() -> StateGraph:
    g = StateGraph(IngestionState)
    g.add_node("discover_candidates", _discover_candidates)
    g.add_node("canonicalize_candidates", _canonicalize_candidates)
    g.add_node("expand_listing_two_level", _expand_listing_two_level)
    g.add_node("decide_access_strategy", _decide_access_strategy)
    g.add_node("fetch_content", _fetch_and_classify)
    g.add_node("extract_document", _extract_documents)
    g.add_node("normalize_document", _normalize_documents)
    g.add_node("dedup_document", _dedup_documents)
    g.add_node("persist_document", _persist_documents)
    g.add_node("update_source_health", _update_source_health)

    g.add_edge(START, "discover_candidates")
    g.add_edge("discover_candidates", "canonicalize_candidates")
    g.add_edge("canonicalize_candidates", "expand_listing_two_level")
    g.add_edge("expand_listing_two_level", "decide_access_strategy")
    g.add_edge("decide_access_strategy", "fetch_content")
    g.add_edge("fetch_content", "extract_document")
    g.add_edge("extract_document", "normalize_document")
    g.add_edge("normalize_document", "dedup_document")
    g.add_edge("dedup_document", "persist_document")
    g.add_edge("persist_document", "update_source_health")
    g.add_edge("update_source_health", END)
    return g
