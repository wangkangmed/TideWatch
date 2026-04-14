"""Events layer node: evidence items -> events + event-evidence links."""

from __future__ import annotations

from typing import Any

from tide_watch.models.graph_state import TideWatchState
from tide_watch.models.pipeline import EventEvidenceLink, EventItem, EvidenceItem


def _evi_field(evi: EvidenceItem | dict, field: str, default: Any = None) -> Any:
    """Read a field from EvidenceItem regardless of whether it is a model or dict."""
    if isinstance(evi, dict):
        return evi.get(field, default)
    return getattr(evi, field, default)


def run_events(state: TideWatchState) -> dict[str, Any]:
    events: list[EventItem] = []
    links: list[EventEvidenceLink] = []
    for idx, evi in enumerate(state.get("evidence_items") or []):
        event_id = f"evt_{idx+1}"
        evi_text = _evi_field(evi, "text", "")
        evi_doc_id = _evi_field(evi, "doc_id", "")
        evi_source_id = _evi_field(evi, "source_id")
        evi_evidence_id = _evi_field(evi, "evidence_id", "")

        events.append(
            EventItem(
                event_id=event_id,
                title=evi_text[:80] or evi_doc_id,
                source_id=evi_source_id,
                supporting_evidence_ids=[evi_evidence_id],
            )
        )
        links.append(
            EventEvidenceLink(
                link_id=f"link_{event_id}_{evi_evidence_id}",
                event_id=event_id,
                evidence_id=evi_evidence_id,
                support_strength=0.7,
            )
        )
    return {
        "events": events,
        "event_evidence_links": links,
        "events_metadata": {"event_count": len(events), "link_count": len(links)},
    }
