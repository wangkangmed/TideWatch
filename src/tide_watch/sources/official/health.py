"""Source health update logic."""

from __future__ import annotations

from datetime import datetime, timezone

from tide_watch.web.block_classifier import is_challenge_block
from tide_watch.models.ingestion import FetchResult, FocusedNormalizedDocument, SourceHealth


def update_health(current: SourceHealth | None, result: FetchResult) -> SourceHealth:
    now = datetime.now(timezone.utc)
    health = current or SourceHealth(source_id=result.source_id)
    health.total_attempts += 1
    health.last_block_reason = result.detected_block_type
    if is_challenge_block(result.detected_block_type):
        health.protected_events += 1
    if health.total_attempts > 0:
        health.protected_rate = min(1.0, health.protected_events / health.total_attempts)
    if result.success:
        health.total_successes += 1
        health.last_success_at = now
        health.failure_reason = None
        if not health.recommended_mode:
            health.recommended_mode = str(health.preferred_mode)
    else:
        health.last_failure_at = now
        health.failure_reason = result.detected_block_type
        if is_challenge_block(result.detected_block_type):
            health.anti_bot_score = min(1.0, health.anti_bot_score + 0.3)
            health.preferred_mode = "metadata_only"
            health.recommended_mode = "metadata_only"
            health.notes = "challenge detected: degrade to metadata/listing"
        elif result.detected_block_type == "rate_limited":
            health.anti_bot_score = min(1.0, health.anti_bot_score + 0.1)
            health.recommended_mode = "listing_only"
        else:
            health.anti_bot_score = max(0.0, health.anti_bot_score - 0.05)
            health.recommended_mode = str(health.preferred_mode)
    if health.total_attempts > 0:
        health.success_rate = health.total_successes / health.total_attempts
    return health


def merge_health_from_normalized_doc(current: SourceHealth | None, doc: FocusedNormalizedDocument) -> SourceHealth:
    """根据入库文档上的 ingestion 标记累计 detail / metadata 统计。"""
    health = current or SourceHealth(source_id=doc.source_id)
    ing = (doc.raw_metadata or {}).get("ingestion") or {}
    health.documents_ingested += 1
    if ing.get("detail_fetch_attempt"):
        health.detail_fetch_attempts += 1
    if ing.get("detail_extract_success"):
        health.detail_fetch_successes += 1
    if ing.get("metadata_fallback"):
        health.metadata_fallback_docs += 1
    if health.detail_fetch_attempts > 0:
        health.detail_success_rate = health.detail_fetch_successes / health.detail_fetch_attempts
    if health.documents_ingested > 0:
        health.metadata_fallback_rate = health.metadata_fallback_docs / health.documents_ingested
    return health
