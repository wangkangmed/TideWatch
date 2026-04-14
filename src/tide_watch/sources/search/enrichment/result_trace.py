"""Utilities for preserving evidence chain for explainability."""

from __future__ import annotations

from tide_watch.sources.search.models import SearchCandidate


def build_trace_payload(candidate: SearchCandidate) -> dict:
    return {
        "candidate_id": candidate.candidate_id,
        "canonical_url": candidate.canonical_url,
        "matched_queries": list(candidate.matched_queries),
        "provider_hits": list(candidate.provider_hits),
        "discovery_channels": list(candidate.discovery_channels),
        "likely_origin_type": candidate.likely_origin_type,
        "score": candidate.score,
        "provider_evidence": candidate.metadata.get("provider_evidence") or [],
    }
