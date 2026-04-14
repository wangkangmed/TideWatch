"""Normalize extracted docs into stable ingestion schema."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from tide_watch.models.ingestion import ExtractedDocument, FetchResult, FocusedNormalizedDocument
from tide_watch.web.url_rules import canonicalize_url


def normalize_document(
    extracted: ExtractedDocument,
    result: FetchResult,
    *,
    source_type: str,
    doc_type_hint: str | None,
) -> FocusedNormalizedDocument:
    canonical = canonicalize_url(extracted.canonical_url or extracted.url)
    content_text = extracted.body_text or ""
    hash_source = (canonical + "|" + (content_text or extracted.title or "")).encode("utf-8")
    content_hash = hashlib.sha256(hash_source).hexdigest()
    document_id = hashlib.sha256(f"{extracted.source_id}:{canonical}".encode("utf-8")).hexdigest()[:24]
    raw_md = dict(extracted.raw_metadata or {})
    if extracted.extracted_fields:
        raw_md.setdefault("extracted_fields", extracted.extracted_fields)
        pt = extracted.extracted_fields.get("page_type")
        if pt:
            raw_md.setdefault("page_type", pt)
        ps = extracted.extracted_fields.get("page_signals")
        if ps is not None:
            raw_md.setdefault("page_signals", ps)
    if extracted.extraction_notes:
        raw_md.setdefault("extraction_notes", extracted.extraction_notes)
    if extracted.updated_at:
        raw_md.setdefault("updated_at", extracted.updated_at.isoformat())
    resolved_doc_type = raw_md.get("normalized_doc_type") or doc_type_hint
    return FocusedNormalizedDocument(
        document_id=document_id,
        company=extracted.company,
        source_id=extracted.source_id,
        source_type=source_type,
        url=extracted.url,
        canonical_url=canonical,
        title=extracted.title,
        published_at=extracted.published_at,
        updated_at=extracted.updated_at,
        ingested_at=datetime.now(timezone.utc),
        doc_type=resolved_doc_type,
        content_text=content_text,
        summary=extracted.summary,
        tags=extracted.tags,
        language=extracted.language,
        access_mode=result.fetch_mode,
        fetch_status=result.status_code,
        blocked_by=result.detected_block_type if result.detected_block_type != "success" else None,
        quality_score=extracted.extraction_quality_score,
        content_hash=content_hash,
        raw_metadata=raw_md,
    )
