"""Official HTML capability adapter.

This module wraps focused-style HTML listing expansion as an internal
capability for the official source branch (not as main DAG orchestration).
"""

from __future__ import annotations

from typing import Iterable

from tide_watch.sources.official.enrichment.listing_expand import expand_listing_seed
from tide_watch.sources.official.source_definitions import CandidateURL, SourceDefinition, SourceRegistryConfig


def apply_official_html_capability(
    candidates: Iterable[CandidateURL],
    *,
    source_config: SourceRegistryConfig | None = None,
    max_child_links: int = 8,
) -> list[CandidateURL]:
    source_map: dict[str, SourceDefinition] = {}
    if source_config is not None:
        for company in source_config.companies:
            for source in company.sources:
                source_map[source.id] = source

    out: list[CandidateURL] = []
    seen: set[str] = set()
    for cand in candidates:
        if cand.url not in seen:
            out.append(cand)
            seen.add(cand.url)
        transport = str((cand.metadata or {}).get("transport") or "")
        if transport != "html_listing" and cand.hint_doc_type != "listing":
            continue
        src_def = source_map.get(cand.source_id)
        for child in expand_listing_seed(cand, source=src_def, max_child_links=max_child_links):
            if child.url in seen:
                continue
            out.append(child)
            seen.add(child.url)
    return out
