"""Access strategy planner for ingestion candidates."""

from __future__ import annotations

from tide_watch.models.ingestion import FetchPlan, SourceAccessMode, SourceHealth
from tide_watch.sources.official.source_definitions import CandidateURL


def decide_access_plan(candidate: CandidateURL, health: SourceHealth | None = None) -> FetchPlan:
    source_access = str(candidate.metadata.get("access") or "").strip().lower()
    source_type = candidate.source_type.lower()
    meta = candidate.metadata or {}
    strategy = str(meta.get("source_strategy") or "fulltext_preferred")
    follow_detail = bool(meta.get("follow_detail_pages", True))

    # 二级：从列表页展开得到的条目 URL
    if meta.get("from_listing_expansion"):
        if source_access == "metadata_only":
            return FetchPlan(
                source_id=candidate.source_id,
                company=candidate.company,
                url=candidate.url,
                mode="metadata_only",
                reason="second_level_respect_metadata_only",
                retryable=False,
                allowed=True,
            )
        if strategy == "protected" or meta.get("protected_policy") == "skip_detail":
            return FetchPlan(
                source_id=candidate.source_id,
                company=candidate.company,
                url=candidate.url,
                mode="metadata_only",
                reason="protected_skip_detail_fetch",
                retryable=False,
                allowed=True,
            )
        if not follow_detail:
            return FetchPlan(
                source_id=candidate.source_id,
                company=candidate.company,
                url=candidate.url,
                mode="metadata_only",
                reason="structured_index_listing_metadata_only",
                retryable=False,
                allowed=True,
            )
        if health and health.anti_bot_score > 0.5:
            return FetchPlan(
                source_id=candidate.source_id,
                company=candidate.company,
                url=candidate.url,
                mode="metadata_only",
                reason="second_level_health_degrade",
                retryable=False,
                allowed=True,
            )
        return FetchPlan(
            source_id=candidate.source_id,
            company=candidate.company,
            url=candidate.url,
            mode="direct_html",
            reason="second_level_article_body",
            retryable=True,
            allowed=True,
        )

    mode: SourceAccessMode = "direct_html"
    reason = "default_direct_html"
    retryable = True

    if source_access in {"metadata_only", "feed_only", "listing_only", "skip"}:
        mode = source_access  # type: ignore[assignment]
        reason = f"source_config_{source_access}"
        retryable = False
    elif source_type in {"rss", "atom"}:
        mode = "feed_only"
        reason = "feed_sources_prefer_feed_only"
        retryable = False
    elif source_type in {"docs", "release_notes", "changelog", "newsroom", "official_blog", "research_blog"}:
        mode = "listing_only"
        reason = "official_listing_first"
        retryable = False
    elif "api." in candidate.url.lower():
        mode = "api"
        reason = "api_like_endpoint"
        retryable = True
    elif "release-notes" in candidate.url.lower() or "changelog" in candidate.url.lower():
        mode = "listing_only"
        reason = "release_notes_prefer_listing"
        retryable = False

    if health and health.anti_bot_score > 0.5:
        mode = "metadata_only"
        reason = "health_anti_bot_degrade"
        retryable = False

    return FetchPlan(
        source_id=candidate.source_id,
        company=candidate.company,
        url=candidate.url,
        mode=mode,
        reason=reason,
        retryable=retryable,
        allowed=True,
    )
