"""Events layer node: normalized docs -> events + event-evidence links."""

from __future__ import annotations

from typing import Any

from tide_watch.models.graph_state import TideWatchState


def run_events(state: TideWatchState) -> dict[str, Any]:
    events: list[dict[str, Any]] = []
    links: list[dict[str, Any]] = []
    for idx, evi in enumerate(state.get("evidence_items") or []):
        event_id = f"evt_{idx+1}"
        event = {
            "event_id": event_id,
            "title": evi.get("text", "")[:80] or evi.get("doc_id"),
            "source_id": evi.get("source_id"),
            "supporting_evidence_ids": [evi.get("evidence_id")],
        }
        events.append(event)
        links.append(
            {
                "link_id": f"link_{event_id}_{evi.get('evidence_id')}",
                "event_id": event_id,
                "evidence_id": evi.get("evidence_id"),
                "support_strength": 0.7,
            }
        )
    return {
        "events": events,
        "event_evidence_links": links,
        "events_metadata": {"event_count": len(events), "link_count": len(links)},
    }
