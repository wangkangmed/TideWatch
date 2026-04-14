"""Bridge ranked search candidates into existing web fetch DTOs."""

from __future__ import annotations

from datetime import datetime, timezone

from tide_watch.models.candidate import CandidateItem
from tide_watch.models.ids import SourceRef
from tide_watch.models.ingestion import FetchPlan
from tide_watch.models.raw import RawFetchBatch, RawRecord
from tide_watch.sources.search.models import RankedSearchCandidate
from tide_watch.web.http_client import run_fetch_plan


def candidate_to_common_candidate(item: RankedSearchCandidate) -> CandidateItem:
    c = item.candidate
    return CandidateItem(
        source_id=f"search:{c.candidate_id}",
        provider="search_discovery",
        transport="html_listing",
        external_id=c.canonical_url or c.url,
        url=c.canonical_url or c.url,
        title=c.title_hint,
        summary=c.summary_hint,
        published_at=c.published_hint,
        metadata={
            "search_route": item.route,
            "fetch_priority": item.fetch_priority,
            "likely_origin_type": c.likely_origin_type,
            "provider_hits": list(c.provider_hits or []),
        },
    )


def build_fetch_plans(items: list[RankedSearchCandidate]) -> list[FetchPlan]:
    plans: list[FetchPlan] = []
    for item in items:
        if item.route != "route_to_web_fetch":
            continue
        c = item.candidate
        plans.append(
            FetchPlan(
                source_id=f"search:{c.candidate_id}",
                company="search_discovery",
                url=c.canonical_url or c.url,
                mode="direct_html",
                reason="search_candidate_fetch",
            )
        )
    return plans


def fetch_candidates_to_raw_batch(items: list[RankedSearchCandidate], *, batch_id: str) -> RawFetchBatch:
    records: list[RawRecord] = []
    errors: list[str] = []
    for item in items:
        if item.route != "route_to_web_fetch":
            continue
        c = item.candidate
        plan = FetchPlan(
            source_id=f"search:{c.candidate_id}",
            company="search_discovery",
            url=c.canonical_url or c.url,
            mode="direct_html",
            reason="search_candidate_fetch",
        )
        result = run_fetch_plan(plan)
        if not result.success:
            errors.append(f"{c.candidate_id}:{result.error or result.status_code}")
            continue
        records.append(
            RawRecord(
                source_ref=SourceRef(provider_id=f"search:{c.candidate_id}", external_id=c.canonical_url or c.url),
                fetched_at=datetime.now(timezone.utc),
                mime_type=result.content_type,
                text=result.raw_text,
                metadata={
                    "url": result.final_url or c.canonical_url or c.url,
                    "search_bridge": True,
                    "origin_type": c.likely_origin_type,
                    "discovery_channels": list(c.discovery_channels or ["web_search"]),
                },
                idempotency_key=f"search:{c.candidate_id}:{c.canonical_url or c.url}",
            )
        )
    return RawFetchBatch(batch_id=batch_id, records=records, errors=errors)
