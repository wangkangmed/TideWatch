"""Dedup logic for normalized documents."""

from __future__ import annotations

from tide_watch.models.ingestion import FocusedNormalizedDocument


def dedup_documents(docs: list[FocusedNormalizedDocument]) -> list[FocusedNormalizedDocument]:
    seen_url: set[str] = set()
    seen_hash: set[str] = set()
    seen_title_date: set[tuple[str, str]] = set()
    out: list[FocusedNormalizedDocument] = []
    for doc in docs:
        canonical = (doc.canonical_url or doc.url or "").strip().lower()
        title_date = ((doc.title or "").strip().lower(), str(doc.published_at or ""))
        if canonical and canonical in seen_url:
            continue
        if doc.content_hash in seen_hash:
            continue
        if title_date[0] and title_date in seen_title_date:
            continue
        if canonical:
            seen_url.add(canonical)
        seen_hash.add(doc.content_hash)
        if title_date[0]:
            seen_title_date.add(title_date)
        out.append(doc)
    return out
