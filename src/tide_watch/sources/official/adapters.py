"""Compatibility adapters between focused ingestion and legacy graph models."""

from __future__ import annotations

from datetime import datetime, timezone

from tide_watch.models.ingestion import FocusedNormalizedDocument
from tide_watch.models.ids import SourceRef
from tide_watch.models.raw import RawFetchBatch, RawRecord


def normalized_to_raw_batch(docs: list[FocusedNormalizedDocument], *, batch_id: str) -> RawFetchBatch:
    records: list[RawRecord] = []
    for doc in docs:
        ref = SourceRef(provider_id=doc.source_id, external_id=doc.canonical_url or doc.url)
        records.append(
            RawRecord(
                source_ref=ref,
                fetched_at=doc.ingested_at if hasattr(doc, "ingested_at") else datetime.now(timezone.utc),
                mime_type="text/plain",
                text=doc.content_text or doc.summary or "",
                metadata={
                    "title": doc.title,
                    "url": doc.canonical_url or doc.url,
                    "source_type": doc.source_type,
                    "blocked_by": doc.blocked_by,
                    "access_mode": doc.access_mode,
                },
                idempotency_key=f"focused:{doc.source_id}:{doc.content_hash[:24]}",
            )
        )
    return RawFetchBatch(batch_id=batch_id, records=records, errors=[])
