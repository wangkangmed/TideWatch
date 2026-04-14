"""Sources layer nodes: official/social/search ingestion orchestration."""

from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone
from typing import Any

from tide_watch.config.settings import TideWatchSettings
from tide_watch.models.graph_state import TideWatchState
from tide_watch.models.ids import SourceRef
from tide_watch.models.raw import RawFetchBatch, RawRecord
from tide_watch.sources.official.config_loader import load_source_config
from tide_watch.sources.official.pipeline import collect_official_discovery
from tide_watch.sources.search.enrichment.fetch_bridge import fetch_candidates_to_raw_batch
from tide_watch.sources.search.pipeline import run_search_discovery
from tide_watch.sources.social.pipeline import collect_social_batches


async def node_collect_official(state: TideWatchState) -> dict[str, Any]:
    cfg_path = state.get("source_config_path")
    cfg = load_source_config(cfg_path)
    settings = TideWatchSettings()
    candidates = collect_official_discovery(
        cfg,
        max_candidates=int(state.get("max_candidates") or settings.focused_max_candidates),
        collection_mode=str(settings.official_collection_mode or "balanced"),
    )
    # Keep official as discovery output in Sources phase; deep html ingestion remains internal capability.
    records = [
        RawRecord(
            source_ref=SourceRef(provider_id=f"official:{c.source_id}", external_id=c.url),
            fetched_at=datetime.now(timezone.utc),
            text=c.url,
            metadata={
                "url": c.url,
                "source_id": c.source_id,
                "company": c.company,
                "transport": (c.metadata or {}).get("transport"),
                "discovery_only": True,
            },
            idempotency_key=f"official:{c.source_id}:{c.url}",
        )
        for c in candidates
    ]
    return {
        "raw_batches": [RawFetchBatch(batch_id="official-discovery", records=records, errors=[])],
        "source_metadata": {"official_candidates": len(candidates)},
    }


async def node_collect_social(state: TideWatchState) -> dict[str, Any]:
    scope = dict(state.get("scope") or {})
    batches, errors, _health = collect_social_batches(
        config_path=state.get("social_config_path"),
        scope=scope,
        run_id=state.get("run_id"),
    )
    return {
        "raw_batches": batches,
        "source_errors": errors,
        "scope": scope,
        "source_metadata": {"social_batches": len(batches)},
    }


async def node_collect_search(state: TideWatchState) -> dict[str, Any]:
    if os.getenv("TIDEWATCH_USE_SEARCH_DISCOVERY", "true").strip().lower() in {"0", "false", "no", "off"}:
        return {}
    ranked, _raw_results = run_search_discovery(config_path=state.get("search_config_path"), top_n=30, min_fetch_score=0.3)
    batch = fetch_candidates_to_raw_batch(ranked, batch_id="search-web-fetch")
    scope = dict(state.get("scope") or {})
    scope["search_last_run"] = {"ranked_candidates": len(ranked)}
    return {"raw_batches": [batch], "scope": scope, "source_metadata": {"search_ranked": len(ranked)}}


def run_sources(state: TideWatchState) -> dict[str, Any]:
    official = asyncio.run(node_collect_official(state))
    social = asyncio.run(node_collect_social(state))
    search = asyncio.run(node_collect_search(state))
    batches = []
    for chunk in (official, social, search):
        batches.extend(chunk.get("raw_batches") or [])
    errors = []
    for chunk in (official, social, search):
        errors.extend(chunk.get("source_errors") or [])
    merged_scope = dict(state.get("scope") or {})
    for chunk in (official, social, search):
        if isinstance(chunk.get("scope"), dict):
            merged_scope.update(chunk["scope"])
    return {
        "raw_batches": batches,
        "source_errors": errors,
        "scope": merged_scope,
        "source_metadata": {
            "official": official.get("source_metadata", {}),
            "social": social.get("source_metadata", {}),
            "search": search.get("source_metadata", {}),
        },
    }
