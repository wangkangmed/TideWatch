"""Source strategy defaults and helpers (capability / fetch behavior)."""

from __future__ import annotations

from typing import Any

from tide_watch.models.ingestion import SourceStrategy
from tide_watch.sources.official.source_definitions import SourceDefinition, SourceRegistryConfig


def infer_source_strategy(source: SourceDefinition) -> SourceStrategy:
    if source.source_strategy:
        return source.source_strategy  # type: ignore[return-value]
    sid = source.id.lower()
    if sid in {"openai_news", "openai_research", "openai_product", "xai_news"}:
        return "protected"
    if "changelog" in sid or "release_notes" in sid:
        return "structured_index"
    if sid in {"anthropic_news", "meta_ai_blog", "microsoft_ai_news", "nvidia_blog"}:
        return "fulltext_preferred"
    if source.access == "metadata_only":
        return "metadata_preferred"
    return "fulltext_preferred"


def effective_follow_detail_pages(source: SourceDefinition) -> bool:
    if source.follow_detail_pages is not None:
        return bool(source.follow_detail_pages)
    strat = infer_source_strategy(source)
    if strat in ("structured_index", "protected", "metadata_preferred"):
        return False
    return True


def effective_metadata_fallback(source: SourceDefinition) -> bool:
    if source.metadata_fallback is not None:
        return bool(source.metadata_fallback)
    return True


def strategy_metadata_for_candidate(source: SourceDefinition) -> dict[str, Any]:
    strat = infer_source_strategy(source)
    meta: dict[str, Any] = {
        "source_strategy": strat,
        "preferred_discovery_mode": source.preferred_discovery_mode or "auto",
        "follow_detail_pages": effective_follow_detail_pages(source),
        "metadata_fallback": effective_metadata_fallback(source),
        "protected_policy": source.protected_policy or "degrade",
        "content_quality_expectation": source.content_quality_expectation or "medium",
        "listing_selectors": dict(source.listing_selectors or {}),
    }
    if source.display_name:
        meta["display_name"] = source.display_name
    return meta


def source_def_from_config_dict(cfg: dict[str, Any] | None, source_id: str) -> SourceDefinition | None:
    if not cfg:
        return None
    companies = cfg.get("companies") or []
    for comp in companies:
        for s in comp.get("sources") or []:
            if s.get("id") == source_id:
                return SourceDefinition.model_validate(s)
    return None


def load_registry_config(cfg: dict[str, Any]) -> SourceRegistryConfig | None:
    if not cfg:
        return None
    try:
        return SourceRegistryConfig.model_validate(cfg)
    except Exception:
        return None
