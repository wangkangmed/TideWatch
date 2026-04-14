"""Listing/newsroom/docs page discovery (metadata-first)."""

from __future__ import annotations

from datetime import datetime, timezone

from tide_watch.sources.official.source_definitions import CandidateURL, SourceDefinition
from tide_watch.sources.official.strategies.source_strategy import strategy_metadata_for_candidate


def discover_from_listing(
    company: str,
    source: SourceDefinition,
    *,
    listing_url: str | None = None,
) -> list[CandidateURL]:
    strat_meta = strategy_metadata_for_candidate(source)
    seed = (listing_url or source.url).strip()
    return [
        CandidateURL(
            source_id=source.id,
            company=company,
            url=seed,
            discovered_at=datetime.now(timezone.utc),
            source_type=source.type,
            hint_doc_type="listing",
            priority=70,
            metadata={"seed": True, "access": source.access, **strat_meta},
        )
    ]
