"""候选项 / 增强结果 -> RawRecord，供主图 normalize 节点消费。"""

from __future__ import annotations

from datetime import datetime, timezone

from tide_watch.models.ids import SourceRef
from tide_watch.models.raw import RawFetchBatch, RawRecord
from tide_watch.sources.social.models import SocialCandidateItem, SocialSourceConfig
from tide_watch.sources.social.ranking import compute_quality_score, engagement_score_from_signals


def candidate_to_raw_record(
    item: SocialCandidateItem,
    source: SocialSourceConfig,
    *,
    metadata_only: bool = False,
) -> RawRecord:
    now = datetime.now(timezone.utc)
    body = (item.text or item.summary or "").strip()
    if not body and item.title:
        body = item.title
    eng = engagement_score_from_signals(item.engagement, item.platform)
    has_cc = bool((item.metadata or {}).get("comment_context"))
    qual = compute_quality_score(
        item,
        content_text=body,
        trust_tier=source.trust_tier,
        has_comment_context=has_cc,
        metadata_only=metadata_only,
    )
    published_iso = item.published_at.isoformat() if item.published_at else None
    meta = {
        "title": item.title,
        "url": item.url,
        "published_at": published_iso,
        "platform": item.platform,
        "social_source_id": source.source_id,
        "source_type": item.source_type,
        "external_id": item.external_id,
        "engagement": item.engagement,
        "engagement_score": eng,
        "quality_score": qual,
        "trust_tier": source.trust_tier,
        "metadata_fallback": metadata_only,
        "social": {
            "author_handle": item.author_handle,
            "summary": item.summary,
            "metadata": item.metadata,
        },
    }
    ref = SourceRef(provider_id=f"social:{source.source_id}", external_id=item.external_id)
    return RawRecord(
        source_ref=ref,
        fetched_at=now,
        mime_type="text/plain",
        text=body,
        metadata=meta,
        idempotency_key=f"social:{source.source_id}:{item.external_id}",
    )


def metadata_fallback_batch(
    candidates: list[SocialCandidateItem],
    source: SocialSourceConfig,
    *,
    batch_id: str,
) -> RawFetchBatch:
    """enrich 全失败时仅用 discovery 字段入库。"""
    recs = [candidate_to_raw_record(c, source, metadata_only=True) for c in candidates]
    return RawFetchBatch(batch_id=batch_id, records=recs, errors=["metadata_fallback: used discovery-only records"])


def enriched_candidates_to_raw_batch(
    items: list[SocialCandidateItem],
    *,
    source: SocialSourceConfig,
    batch_id: str,
    errors: list[str] | None = None,
) -> RawFetchBatch:
    recs = [candidate_to_raw_record(it, source, metadata_only=False) for it in items]
    return RawFetchBatch(batch_id=batch_id, records=recs, errors=list(errors or []))
