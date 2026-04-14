"""Persistence node: writes all five-layer outputs to PipelineRepository."""

from __future__ import annotations

import uuid
from typing import Any

from tide_watch.models.graph_state import TideWatchState
from tide_watch.storage.pipeline_repository import PipelineRepository


def persist_pipeline_results(state: TideWatchState) -> dict[str, Any]:
    run_id = state.get("run_id") or uuid.uuid4().hex[:12]
    repo = PipelineRepository()

    repo.start_run(run_id, metadata=state.get("source_metadata"))

    repo.save_documents(run_id, state.get("normalized_docs") or [])
    repo.save_evidence(run_id, state.get("evidence_items") or [])

    repo.save_events(
        run_id,
        state.get("events") or [],
        state.get("event_evidence_links") or [],
    )

    repo.save_intelligence(
        run_id,
        state.get("trends") or [],
        state.get("findings") or [],
        state.get("alerts") or [],
        state.get("briefing_items") or [],
    )

    repo.save_decision_support(
        run_id,
        state.get("decision_signals") or [],
        state.get("recommendation_items") or [],
        state.get("decision_briefs") or [],
    )

    repo.finish_run(run_id, status="completed")
    return {}
