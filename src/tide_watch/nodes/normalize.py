"""Evidence layer nodes: raw batches -> normalized docs + evidence items."""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any

from tide_watch.models.graph_state import TideWatchState
from tide_watch.models.ids import SourceRef
from tide_watch.models.normalized import NormalizedDocument


def _parse_dt(raw: Any) -> datetime | None:
    if isinstance(raw, datetime):
        return raw
    if isinstance(raw, str) and raw:
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def node_normalize_batch(state: TideWatchState) -> dict[str, Any]:
    docs: list[NormalizedDocument] = []
    evidence_items: list[dict[str, Any]] = []
    for batch in state.get("raw_batches") or []:
        for rec in batch.records:
            text = rec.text or (rec.body_bytes.decode("utf-8", errors="ignore") if rec.body_bytes else "")
            md = dict(rec.metadata or {})
            provider = rec.source_ref.provider_id
            source_id = md.get("source_id") or provider
            canonical_url = md.get("url")
            doc_id = hashlib.sha256(f"{provider}:{rec.source_ref.external_id}:{canonical_url or ''}".encode()).hexdigest()[:24]
            source_ref = SourceRef(provider_id=provider, external_id=rec.source_ref.external_id)
            doc = NormalizedDocument(
                doc_id=doc_id,
                source_ref=source_ref,
                source_id=source_id,
                origin_type=md.get("origin_type", "unknown"),
                discovery_channels=list(md.get("discovery_channels") or []),
                title=md.get("title"),
                canonical_url=canonical_url,
                published_at=_parse_dt(md.get("published_at")),
                updated_at=_parse_dt(md.get("updated_at")),
                language=md.get("language"),
                body_text=text,
                page_type=md.get("page_type"),
                raw_metadata=md,
                fingerprint=hashlib.sha256((text or canonical_url or doc_id).encode()).hexdigest(),
            )
            docs.append(doc)
            evidence_items.append(
                {
                    "evidence_id": f"evi_{doc_id}",
                    "doc_id": doc_id,
                    "source_id": source_id,
                    "source_trace": {
                        "provider_id": provider,
                        "external_id": rec.source_ref.external_id,
                        "discovery_channels": list(md.get("discovery_channels") or []),
                    },
                    "text": (text or "")[:1000],
                }
            )
    return {
        "normalized_docs": docs,
        "evidence_items": evidence_items,
        "evidence_metadata": {"raw_batches": len(state.get("raw_batches") or []), "normalized_docs": len(docs)},
    }


def build_evidence(state: TideWatchState) -> dict[str, Any]:
    return node_normalize_batch(state)
