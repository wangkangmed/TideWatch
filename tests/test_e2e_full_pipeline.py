"""End-to-end test for the five-layer TideWatch pipeline.

Validates data flow, state propagation, storage persistence,
and traceability across all five layers using mock data
(no network access required).
"""

from __future__ import annotations

import json
import sqlite3
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from tide_watch.graph.main_graph import build_main_graph, compile_app
from tide_watch.models.graph_state import TideWatchState
from tide_watch.models.ids import SourceRef
from tide_watch.models.ingestion import (
    FetchAttempt,
    FocusedNormalizedDocument,
    SourceHealth,
)
from tide_watch.models.normalized import NormalizedDocument
from tide_watch.models.raw import RawFetchBatch, RawRecord
from tide_watch.nodes.collect import run_sources
from tide_watch.nodes.decision_support import run_decision_support
from tide_watch.nodes.events import run_events
from tide_watch.nodes.intelligence import run_intelligence
from tide_watch.nodes.normalize import build_evidence
from tide_watch.sources.official.persistence import IngestionRepository


# ---------------------------------------------------------------------------
# Fixtures: synthetic data that exercises all code paths
# ---------------------------------------------------------------------------

def _make_raw_batches() -> list[RawFetchBatch]:
    """Create realistic RawFetchBatch records from multiple source types."""
    now = datetime.now(timezone.utc)
    records_official = [
        RawRecord(
            source_ref=SourceRef(provider_id="official:openai_news", external_id="https://openai.com/news/item-1"),
            fetched_at=now,
            text="OpenAI announces GPT-5 with reasoning capabilities",
            metadata={
                "url": "https://openai.com/news/item-1",
                "source_id": "openai_news",
                "company": "OpenAI",
                "transport": "rss",
                "title": "GPT-5 Announcement",
                "published_at": "2026-04-10T10:00:00+00:00",
                "discovery_channels": ["rss"],
                "origin_type": "newsroom",
                "page_type": "article",
            },
            idempotency_key="official:openai_news:https://openai.com/news/item-1",
        ),
        RawRecord(
            source_ref=SourceRef(provider_id="official:anthropic_news", external_id="https://anthropic.com/news/item-2"),
            fetched_at=now,
            text="Anthropic releases Claude 4 with improved safety features and extended context",
            metadata={
                "url": "https://anthropic.com/news/item-2",
                "source_id": "anthropic_news",
                "company": "Anthropic",
                "transport": "html_listing",
                "title": "Claude 4 Release",
                "published_at": "2026-04-11T14:30:00+00:00",
                "discovery_channels": ["html_listing"],
                "origin_type": "newsroom",
                "page_type": "article",
            },
            idempotency_key="official:anthropic_news:https://anthropic.com/news/item-2",
        ),
    ]
    records_social = [
        RawRecord(
            source_ref=SourceRef(provider_id="social:reddit:LocalLLaMA", external_id="post_abc123"),
            fetched_at=now,
            text="Discussion: GPT-5 vs Claude 4 benchmarks show interesting tradeoffs in reasoning",
            metadata={
                "url": "https://reddit.com/r/LocalLLaMA/comments/abc123",
                "source_id": "reddit_local_llm",
                "platform": "reddit",
                "title": "GPT-5 vs Claude 4 Benchmark Comparison",
                "published_at": "2026-04-12T08:00:00+00:00",
                "discovery_channels": ["subreddit_feed"],
                "origin_type": "social",
            },
            idempotency_key="social:reddit:post_abc123",
        ),
    ]
    records_search = [
        RawRecord(
            source_ref=SourceRef(provider_id="search:newsapi_1", external_id="https://techcrunch.com/2026/04/gpt5"),
            fetched_at=now,
            text="TechCrunch analysis of GPT-5 launch and its impact on the AI industry",
            metadata={
                "url": "https://techcrunch.com/2026/04/gpt5",
                "source_id": "search:newsapi_1",
                "title": "GPT-5 Launch Analysis",
                "published_at": "2026-04-10T18:00:00+00:00",
                "discovery_channels": ["web_search"],
                "origin_type": "third_party_media",
                "search_bridge": True,
            },
            idempotency_key="search:newsapi_1:https://techcrunch.com/2026/04/gpt5",
        ),
    ]
    return [
        RawFetchBatch(batch_id="official-discovery", records=records_official, errors=[]),
        RawFetchBatch(batch_id="social-reddit-demo", records=records_social, errors=["x_openai:timeout"]),
        RawFetchBatch(batch_id="search-web-fetch", records=records_search, errors=[]),
    ]


# ===========================================================================
# Test 1: Layer-by-layer data flow validation
# ===========================================================================

class TestLayerByLayerDataFlow:
    """Run each layer independently to verify correct data propagation."""

    def test_layer1_sources_output_structure(self, monkeypatch):
        """Sources layer should produce raw_batches, source_errors, source_metadata."""
        async def mock_official(_s):
            return {"raw_batches": [_make_raw_batches()[0]], "source_metadata": {"official_candidates": 2}}
        async def mock_social(_s):
            return {"raw_batches": [_make_raw_batches()[1]], "source_errors": ["x_openai:timeout"], "source_metadata": {"social_batches": 1}}
        async def mock_search(_s):
            return {"raw_batches": [_make_raw_batches()[2]], "source_metadata": {"search_ranked": 1}}

        monkeypatch.setattr("tide_watch.nodes.collect.node_collect_official", mock_official)
        monkeypatch.setattr("tide_watch.nodes.collect.node_collect_social", mock_social)
        monkeypatch.setattr("tide_watch.nodes.collect.node_collect_search", mock_search)

        result = run_sources({"scope": {}})

        assert "raw_batches" in result
        assert len(result["raw_batches"]) == 3
        assert "source_errors" in result
        assert "x_openai:timeout" in result["source_errors"]
        assert "source_metadata" in result
        for key in ("official", "social", "search"):
            assert key in result["source_metadata"]
        total_records = sum(len(b.records) for b in result["raw_batches"])
        assert total_records == 4

    def test_layer2_evidence_builds_from_raw_batches(self):
        """Evidence layer should normalize raw batches into docs + evidence items."""
        state: TideWatchState = {"raw_batches": _make_raw_batches()}
        result = build_evidence(state)

        assert "normalized_docs" in result
        assert "evidence_items" in result
        assert "evidence_metadata" in result
        assert len(result["normalized_docs"]) == 4
        assert len(result["evidence_items"]) == 4

        for doc in result["normalized_docs"]:
            assert isinstance(doc, NormalizedDocument)
            assert doc.doc_id
            assert doc.fingerprint
            assert doc.source_ref

        for evi in result["evidence_items"]:
            assert evi["evidence_id"].startswith("evi_")
            assert evi["doc_id"]
            assert "source_trace" in evi

    def test_layer2_evidence_preserves_metadata(self):
        """Evidence layer should carry forward title, URL, published_at from raw records."""
        state: TideWatchState = {"raw_batches": _make_raw_batches()}
        result = build_evidence(state)

        urls_found = {doc.canonical_url for doc in result["normalized_docs"]}
        assert "https://openai.com/news/item-1" in urls_found
        assert "https://anthropic.com/news/item-2" in urls_found

    def test_layer3_events_from_evidence(self):
        """Events layer should create one event per evidence item."""
        state: TideWatchState = {"raw_batches": _make_raw_batches()}
        evidence_result = build_evidence(state)

        state_with_evidence = {**state, **evidence_result}
        events_result = run_events(state_with_evidence)

        assert "events" in events_result
        assert "event_evidence_links" in events_result
        assert len(events_result["events"]) == 4
        assert len(events_result["event_evidence_links"]) == 4

        for evt in events_result["events"]:
            assert evt["event_id"].startswith("evt_")
            assert "supporting_evidence_ids" in evt
            assert len(evt["supporting_evidence_ids"]) == 1

        for link in events_result["event_evidence_links"]:
            assert "link_id" in link
            assert "event_id" in link
            assert "evidence_id" in link
            assert link["support_strength"] == 0.7

    def test_layer4_intelligence_from_events(self):
        """Intelligence layer should produce trends, findings, alerts, briefings."""
        state: TideWatchState = {"raw_batches": _make_raw_batches()}
        evidence = build_evidence(state)
        events = run_events({**state, **evidence})

        intel = run_intelligence({**state, **evidence, **events})

        assert len(intel["trends"]) == 4
        assert len(intel["findings"]) == 4
        assert len(intel["alerts"]) >= 1
        assert len(intel["briefing_items"]) >= 1

        for trend in intel["trends"]:
            assert trend["trend_id"].startswith("tr_")
            assert "supporting_event_ids" in trend
        for finding in intel["findings"]:
            assert finding["finding_id"].startswith("fd_")
            assert "supporting_event_ids" in finding
            assert "supporting_evidence_ids" in finding

    def test_layer5_decision_support_from_intelligence(self):
        """Decision support should produce signals, recommendations, briefs."""
        state: TideWatchState = {"raw_batches": _make_raw_batches()}
        evidence = build_evidence(state)
        events = run_events({**state, **evidence})
        intel = run_intelligence({**state, **evidence, **events})

        decision = run_decision_support({**state, **evidence, **events, **intel})

        assert len(decision["decision_signals"]) == 4
        assert len(decision["recommendation_items"]) == 4
        assert len(decision["decision_briefs"]) >= 1

        for sig in decision["decision_signals"]:
            assert sig["signal_id"].startswith("ds_")
            assert "finding_id" in sig
            assert "supporting_finding_ids" in sig
            assert "supporting_event_ids" in sig
            assert "supporting_evidence_ids" in sig

        for rec in decision["recommendation_items"]:
            assert rec["recommendation_id"].startswith("rec_")
            assert "recommended_action" in rec


# ===========================================================================
# Test 2: Full graph execution (mocked sources, real logic for layers 2-5)
# ===========================================================================

class TestFullGraphExecution:
    """Run the compiled LangGraph from start to end."""

    def test_full_graph_produces_all_layers(self, monkeypatch):
        """Full graph invocation should populate all five layer outputs."""
        monkeypatch.setattr(
            "tide_watch.graph.main_graph.run_sources",
            lambda _s: {
                "raw_batches": _make_raw_batches(),
                "source_errors": [],
                "source_metadata": {"official": {}, "social": {}, "search": {}},
            },
        )

        app = compile_app()
        out = app.invoke({"run_id": "e2e_test_001", "scope": {}})

        assert out.get("raw_batches") is not None
        assert len(out["raw_batches"]) == 3

        assert out.get("normalized_docs") is not None
        assert len(out["normalized_docs"]) == 4
        assert out.get("evidence_items") is not None
        assert len(out["evidence_items"]) == 4

        assert out.get("events") is not None
        assert len(out["events"]) == 4

        assert out.get("trends") is not None
        assert len(out["trends"]) == 4
        assert out.get("findings") is not None
        assert out.get("alerts") is not None

        assert out.get("decision_signals") is not None
        assert len(out["decision_signals"]) == 4
        assert out.get("recommendation_items") is not None
        assert out.get("decision_briefs") is not None

    def test_empty_input_produces_empty_output(self, monkeypatch):
        """With zero raw data, all downstream layers should still succeed (empty lists)."""
        monkeypatch.setattr(
            "tide_watch.graph.main_graph.run_sources",
            lambda _s: {"raw_batches": [], "source_errors": [], "source_metadata": {}},
        )
        app = compile_app()
        out = app.invoke({"run_id": "e2e_empty", "scope": {}})

        assert out.get("normalized_docs") == []
        assert out.get("events") == []
        assert out.get("trends") == []
        assert out.get("findings") == []
        assert out.get("decision_signals") == []
        assert out.get("recommendation_items") == []
        assert out.get("decision_briefs") == []


# ===========================================================================
# Test 3: Data traceability across all five layers
# ===========================================================================

class TestTraceability:
    """Verify that IDs form a complete chain from Layer 5 back to Layer 1."""

    @pytest.fixture
    def full_pipeline_output(self, monkeypatch) -> dict[str, Any]:
        monkeypatch.setattr(
            "tide_watch.graph.main_graph.run_sources",
            lambda _s: {
                "raw_batches": _make_raw_batches(),
                "source_errors": [],
                "source_metadata": {},
            },
        )
        app = compile_app()
        return app.invoke({"run_id": "trace_test", "scope": {}})

    def test_evidence_ids_match_documents(self, full_pipeline_output):
        out = full_pipeline_output
        doc_ids = {d.doc_id for d in out["normalized_docs"]}
        for evi in out["evidence_items"]:
            assert evi["doc_id"] in doc_ids, f"Evidence doc_id={evi['doc_id']} not in normalized_docs"

    def test_event_evidence_links_valid(self, full_pipeline_output):
        out = full_pipeline_output
        evi_ids = {e["evidence_id"] for e in out["evidence_items"]}
        evt_ids = {e["event_id"] for e in out["events"]}
        for link in out["event_evidence_links"]:
            assert link["event_id"] in evt_ids
            assert link["evidence_id"] in evi_ids

    def test_findings_reference_valid_events(self, full_pipeline_output):
        out = full_pipeline_output
        evt_ids = {e["event_id"] for e in out["events"]}
        for finding in out["findings"]:
            for eid in finding.get("supporting_event_ids", []):
                assert eid in evt_ids, f"Finding references unknown event_id={eid}"

    def test_decision_signals_reference_valid_findings(self, full_pipeline_output):
        out = full_pipeline_output
        finding_ids = {f["finding_id"] for f in out["findings"]}
        for sig in out["decision_signals"]:
            assert sig["finding_id"] in finding_ids

    def test_full_chain_from_decision_to_raw(self, full_pipeline_output):
        """Walk backward from a decision_signal to the original raw record."""
        out = full_pipeline_output
        sig = out["decision_signals"][0]

        finding = next(f for f in out["findings"] if f["finding_id"] == sig["finding_id"])
        assert finding

        event_id = finding["supporting_event_ids"][0]
        event = next(e for e in out["events"] if e["event_id"] == event_id)
        assert event

        evi_id = event["supporting_evidence_ids"][0]
        evidence = next(e for e in out["evidence_items"] if e["evidence_id"] == evi_id)
        assert evidence

        doc_id = evidence["doc_id"]
        doc = next(d for d in out["normalized_docs"] if d.doc_id == doc_id)
        assert doc
        assert doc.source_ref.provider_id


# ===========================================================================
# Test 4: Storage layer - IngestionRepository
# ===========================================================================

class TestIngestionRepositoryStorage:
    """Test that IngestionRepository correctly persists and loads data."""

    @pytest.fixture
    def repo(self, tmp_path) -> IngestionRepository:
        db = tmp_path / "test_ingestion.sqlite3"
        return IngestionRepository(str(db))

    def test_save_and_load_document(self, repo):
        doc = FocusedNormalizedDocument(
            document_id="doc_test_001",
            company="OpenAI",
            source_id="openai_news",
            source_type="newsroom",
            url="https://openai.com/news/test",
            title="Test Article",
            ingested_at=datetime.now(timezone.utc),
            access_mode="listing_only",
            quality_score=0.8,
            content_hash="abc123hash",
            content_text="Full article text here",
            raw_metadata={"key": "value"},
        )
        repo.save_doc(doc)

        with repo._connect() as conn:
            row = conn.execute(
                "SELECT document_id, title, quality_score, raw_metadata FROM normalized_documents WHERE document_id=?",
                (doc.document_id,),
            ).fetchone()
        assert row is not None
        assert row[0] == "doc_test_001"
        assert row[1] == "Test Article"
        assert row[2] == 0.8
        meta = json.loads(row[3])
        assert meta["key"] == "value"

    def test_save_and_load_fetch_attempt(self, repo):
        attempt = FetchAttempt(
            source_id="openai_news",
            url="https://openai.com/news/test",
            status_code=403,
            block_type="cloudflare_challenge",
            fetch_mode="direct_html",
            retryable=False,
            error="Cloudflare challenge page detected",
            created_at=datetime.now(timezone.utc),
        )
        repo.save_attempt(attempt)

        with repo._connect() as conn:
            row = conn.execute(
                "SELECT source_id, block_type, status_code FROM fetch_attempts WHERE source_id=?",
                ("openai_news",),
            ).fetchone()
        assert row is not None
        assert row[1] == "cloudflare_challenge"
        assert row[2] == 403

    def test_save_and_load_source_health(self, repo):
        health = {
            "openai_news": SourceHealth(
                source_id="openai_news",
                success_rate=0.6,
                total_attempts=10,
                total_successes=6,
                anti_bot_score=0.3,
                preferred_mode="listing_only",
            ),
        }
        repo.save_health(health)
        loaded = repo.load_health()

        assert "openai_news" in loaded
        h = loaded["openai_news"]
        assert h.success_rate == 0.6
        assert h.total_attempts == 10
        assert h.anti_bot_score == 0.3

    def test_upsert_document_replaces(self, repo):
        doc = FocusedNormalizedDocument(
            document_id="doc_upsert",
            company="Anthropic",
            source_id="anthropic_news",
            source_type="newsroom",
            url="https://anthropic.com/test",
            title="Version 1",
            ingested_at=datetime.now(timezone.utc),
            access_mode="listing_only",
            quality_score=0.5,
            content_hash="hash_v1",
            raw_metadata={},
        )
        repo.save_doc(doc)

        doc.title = "Version 2"
        doc.quality_score = 0.9
        repo.save_doc(doc)

        with repo._connect() as conn:
            rows = conn.execute(
                "SELECT title, quality_score FROM normalized_documents WHERE document_id=?",
                ("doc_upsert",),
            ).fetchall()
        assert len(rows) == 1
        assert rows[0][0] == "Version 2"
        assert rows[0][1] == 0.9


# ===========================================================================
# Test 5: State type / reducer issues
# ===========================================================================

class TestStateReducerIssues:
    """Identify potential issues with LangGraph state merging."""

    def test_raw_batches_list_merge_semantics(self, monkeypatch):
        """LangGraph TypedDict replaces lists by default.
        If sources layer returns batches from only one sub-collector,
        the other sub-collector results would be overwritten without explicit merge.
        Verify run_sources handles this correctly."""
        async def mock_official(_s):
            return {
                "raw_batches": [RawFetchBatch(batch_id="off-1", records=[], errors=[])],
                "source_metadata": {},
            }
        async def mock_social(_s):
            return {
                "raw_batches": [RawFetchBatch(batch_id="soc-1", records=[], errors=[])],
                "source_metadata": {},
            }
        async def mock_search(_s):
            return {
                "raw_batches": [RawFetchBatch(batch_id="sea-1", records=[], errors=[])],
                "source_metadata": {},
            }
        monkeypatch.setattr("tide_watch.nodes.collect.node_collect_official", mock_official)
        monkeypatch.setattr("tide_watch.nodes.collect.node_collect_social", mock_social)
        monkeypatch.setattr("tide_watch.nodes.collect.node_collect_search", mock_search)

        result = run_sources({"scope": {}})
        assert len(result["raw_batches"]) == 3, (
            "run_sources should explicitly merge batches from all three sub-collectors"
        )

    def test_evidence_layer_handles_missing_metadata_fields(self):
        """Evidence layer should not crash on records with minimal metadata."""
        minimal_record = RawRecord(
            source_ref=SourceRef(provider_id="test", external_id="minimal"),
            fetched_at=datetime.now(timezone.utc),
            text="Minimal text content",
            metadata={},
            idempotency_key="test:minimal",
        )
        batch = RawFetchBatch(batch_id="minimal", records=[minimal_record], errors=[])
        result = build_evidence({"raw_batches": [batch]})

        assert len(result["normalized_docs"]) == 1
        doc = result["normalized_docs"][0]
        assert doc.origin_type == "unknown"
        assert doc.canonical_url is None
        assert doc.published_at is None

    def test_events_layer_handles_empty_text(self):
        """Events layer should handle evidence items where text is empty."""
        state = {
            "evidence_items": [
                {
                    "evidence_id": "evi_empty",
                    "doc_id": "doc_empty",
                    "source_id": "test",
                    "text": "",
                    "source_trace": {},
                }
            ]
        }
        result = run_events(state)
        assert len(result["events"]) == 1
        assert result["events"][0]["title"] == "doc_empty"

    def test_intelligence_preserves_evidence_ids_from_events(self):
        """Intelligence layer should carry forward supporting_evidence_ids from events."""
        state = {
            "events": [
                {
                    "event_id": "evt_1",
                    "title": "Test",
                    "source_id": "test",
                    "supporting_evidence_ids": ["evi_a", "evi_b"],
                }
            ]
        }
        result = run_intelligence(state)
        finding = result["findings"][0]
        assert "evi_a" in finding["supporting_evidence_ids"]
        assert "evi_b" in finding["supporting_evidence_ids"]

    def test_decision_support_with_no_findings(self):
        """Decision support should handle empty findings gracefully."""
        result = run_decision_support({"findings": []})
        assert result["decision_signals"] == []
        assert result["recommendation_items"] == []
        assert result["decision_briefs"] == []


# ===========================================================================
# Test 6: Persistence gap - main graph does NOT persist to SQLite
# ===========================================================================

class TestPersistenceGap:
    """Demonstrate that the main graph layers 2-5 do NOT persist results.

    The focused/graph.py subgraph has a _persist_documents node,
    but the main five-layer graph (graph/main_graph.py) has no persistence.
    """

    def test_main_graph_does_not_persist_to_sqlite(self, monkeypatch, tmp_path):
        """Run full graph and verify no data ends up in any SQLite file."""
        monkeypatch.setattr(
            "tide_watch.graph.main_graph.run_sources",
            lambda _s: {
                "raw_batches": _make_raw_batches(),
                "source_errors": [],
                "source_metadata": {},
            },
        )
        db_path = tmp_path / "check_persist.sqlite3"

        app = compile_app()
        out = app.invoke({"run_id": "persist_check", "scope": {}})

        assert len(out["normalized_docs"]) > 0
        assert len(out["decision_signals"]) > 0
        assert not db_path.exists(), "No SQLite file should be auto-created by the main graph"

    def test_focused_subgraph_has_persist_node(self):
        """Verify focused subgraph includes the persist step."""
        from tide_watch.focused.graph import build_ingestion_subgraph
        g = build_ingestion_subgraph()
        compiled = g.compile()
        mermaid = compiled.get_graph().draw_mermaid()
        assert "persist_document" in mermaid
        assert "update_source_health" in mermaid


# ===========================================================================
# Test 7: ID uniqueness and deduplication
# ===========================================================================

class TestIdUniqueness:

    def test_document_ids_are_unique(self):
        state: TideWatchState = {"raw_batches": _make_raw_batches()}
        result = build_evidence(state)
        doc_ids = [d.doc_id for d in result["normalized_docs"]]
        assert len(doc_ids) == len(set(doc_ids)), "Document IDs should be unique"

    def test_evidence_ids_are_unique(self):
        state: TideWatchState = {"raw_batches": _make_raw_batches()}
        result = build_evidence(state)
        evi_ids = [e["evidence_id"] for e in result["evidence_items"]]
        assert len(evi_ids) == len(set(evi_ids)), "Evidence IDs should be unique"

    def test_duplicate_records_produce_different_doc_ids(self):
        """Two records with same URL but different providers should produce different doc_ids."""
        now = datetime.now(timezone.utc)
        r1 = RawRecord(
            source_ref=SourceRef(provider_id="official:src_a", external_id="https://example.com/article"),
            fetched_at=now,
            text="Same article text",
            metadata={"url": "https://example.com/article"},
            idempotency_key="off:a:url",
        )
        r2 = RawRecord(
            source_ref=SourceRef(provider_id="search:src_b", external_id="https://example.com/article"),
            fetched_at=now,
            text="Same article text",
            metadata={"url": "https://example.com/article"},
            idempotency_key="search:b:url",
        )
        batch = RawFetchBatch(batch_id="dedup-test", records=[r1, r2], errors=[])
        result = build_evidence({"raw_batches": [batch]})
        ids = [d.doc_id for d in result["normalized_docs"]]
        assert len(ids) == 2
        assert ids[0] != ids[1], (
            "Same URL from different providers should produce distinct doc_ids, "
            "but same URL from same provider would collide due to hash input"
        )

    def test_same_provider_same_url_produces_same_doc_id(self):
        """Idempotent: same provider + same URL should produce the same doc_id."""
        now = datetime.now(timezone.utc)
        rec = RawRecord(
            source_ref=SourceRef(provider_id="official:src_x", external_id="https://example.com/a"),
            fetched_at=now,
            text="Article",
            metadata={"url": "https://example.com/a"},
            idempotency_key="off:x:a",
        )
        batch1 = RawFetchBatch(batch_id="run1", records=[rec], errors=[])
        batch2 = RawFetchBatch(batch_id="run2", records=[rec], errors=[])

        r1 = build_evidence({"raw_batches": [batch1]})
        r2 = build_evidence({"raw_batches": [batch2]})
        assert r1["normalized_docs"][0].doc_id == r2["normalized_docs"][0].doc_id


# ===========================================================================
# Test 8: IngestionRepository schema completeness
# ===========================================================================

class TestIngestionRepositorySchema:
    """Check the IngestionRepository schema against FocusedNormalizedDocument fields."""

    def test_schema_covers_all_required_fields(self, tmp_path):
        repo = IngestionRepository(str(tmp_path / "schema_test.sqlite3"))
        with repo._connect() as conn:
            info = conn.execute("PRAGMA table_info(normalized_documents)").fetchall()
        col_names = {row[1] for row in info}

        doc_model_fields = set(FocusedNormalizedDocument.model_fields.keys())
        critical_fields = {"document_id", "source_id", "url", "title", "content_text", "quality_score"}
        for f in critical_fields:
            assert f in col_names, f"Critical field '{f}' missing from DB schema"

        missing_in_db = doc_model_fields - col_names
        extra_in_db = col_names - doc_model_fields

        NOT_IN_DB = {"updated_at", "content_hash"}
        missing_in_db -= NOT_IN_DB
        if "content_hash" not in col_names:
            pass
