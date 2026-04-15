"""Normalization and storage round-trip tests for every pipeline layer.

Goal: verify that data at each layer is normalized correctly and that
storage write/read cycles preserve data integrity.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any

import pytest

from tide_watch.models.ids import SourceRef
from tide_watch.models.ingestion import (
    FetchAttempt,
    FocusedNormalizedDocument,
    SourceHealth,
)
from tide_watch.models.normalized import NormalizedDocument
from tide_watch.models.pipeline import (
    AlertItem,
    BriefingItem,
    DecisionBrief,
    DecisionSignal,
    EventEvidenceLink,
    EventItem,
    EvidenceItem,
    Finding,
    RecommendationItem,
    TrendSignal,
)
from tide_watch.models.raw import RawFetchBatch, RawRecord
from tide_watch.nodes.normalize import build_evidence
from tide_watch.nodes.events import run_events
from tide_watch.nodes.intelligence import run_intelligence
from tide_watch.nodes.decision_support import run_decision_support
from tide_watch.sources.official.persistence import IngestionRepository


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

NOW = datetime(2026, 4, 14, 12, 0, 0, tzinfo=timezone.utc)


def _rich_raw_batches() -> list[RawFetchBatch]:
    """Create raw batches with full metadata for thorough normalization tests."""
    return [
        RawFetchBatch(
            batch_id="official-batch",
            records=[
                RawRecord(
                    source_ref=SourceRef(
                        provider_id="official:openai_news",
                        external_id="https://openai.com/news/gpt5",
                    ),
                    fetched_at=NOW,
                    text="OpenAI announces GPT-5 with breakthrough reasoning",
                    metadata={
                        "url": "https://openai.com/news/gpt5",
                        "source_id": "openai_news",
                        "company": "OpenAI",
                        "transport": "rss",
                        "title": "GPT-5 Announcement",
                        "published_at": "2026-04-10T10:00:00+00:00",
                        "updated_at": "2026-04-11T08:00:00+00:00",
                        "discovery_channels": ["rss", "sitemap"],
                        "origin_type": "newsroom",
                        "page_type": "article",
                        "language": "en",
                    },
                    idempotency_key="official:openai_news:gpt5",
                ),
                RawRecord(
                    source_ref=SourceRef(
                        provider_id="official:anthropic_news",
                        external_id="https://anthropic.com/news/claude4",
                    ),
                    fetched_at=NOW,
                    text="",
                    metadata={
                        "url": "https://anthropic.com/news/claude4",
                        "source_id": "anthropic_news",
                    },
                    idempotency_key="official:anthropic_news:claude4",
                ),
            ],
            errors=[],
        ),
        RawFetchBatch(
            batch_id="social-batch",
            records=[
                RawRecord(
                    source_ref=SourceRef(
                        provider_id="social:reddit:LocalLLaMA",
                        external_id="post_xyz",
                    ),
                    fetched_at=NOW,
                    text="Great discussion about GPT-5 benchmarks",
                    metadata={
                        "url": "https://reddit.com/r/LocalLLaMA/xyz",
                        "source_id": "reddit_local_llm",
                        "platform": "reddit",
                        "title": "GPT-5 Benchmarks",
                        "published_at": "bad-date-format",
                        "discovery_channels": ["subreddit_feed"],
                        "origin_type": "social",
                    },
                    idempotency_key="social:reddit:post_xyz",
                ),
            ],
            errors=["x_openai:connection_timeout"],
        ),
    ]


# ===========================================================================
# Layer 1: Sources → raw data normalization
# ===========================================================================

class TestLayer1SourceNormalization:
    """Verify that RawRecord/RawFetchBatch models validate and hold data correctly."""

    def test_raw_record_fields_complete(self):
        batch = _rich_raw_batches()[0]
        rec = batch.records[0]

        assert rec.source_ref.provider_id == "official:openai_news"
        assert rec.source_ref.external_id == "https://openai.com/news/gpt5"
        assert rec.fetched_at == NOW
        assert rec.text == "OpenAI announces GPT-5 with breakthrough reasoning"
        assert rec.idempotency_key == "official:openai_news:gpt5"
        assert rec.metadata["url"] == "https://openai.com/news/gpt5"
        assert rec.metadata["transport"] == "rss"

    def test_raw_batch_error_handling(self):
        batch = _rich_raw_batches()[1]
        assert batch.batch_id == "social-batch"
        assert len(batch.errors) == 1
        assert "x_openai" in batch.errors[0]

    def test_raw_record_with_empty_text(self):
        batch = _rich_raw_batches()[0]
        empty_rec = batch.records[1]
        assert empty_rec.text == ""
        assert empty_rec.metadata.get("title") is None

    def test_raw_record_with_body_bytes(self):
        rec = RawRecord(
            source_ref=SourceRef(provider_id="test", external_id="bin"),
            fetched_at=NOW,
            text=None,
            body_bytes=b"Binary content here",
            metadata={},
            idempotency_key="test:bin",
        )
        assert rec.body_bytes == b"Binary content here"
        assert rec.text is None


# ===========================================================================
# Layer 2: Evidence normalization
# ===========================================================================

class TestLayer2EvidenceNormalization:
    """Verify build_evidence produces correctly normalized documents and evidence items."""

    @pytest.fixture
    def evidence_result(self) -> dict[str, Any]:
        return build_evidence({"raw_batches": _rich_raw_batches()})

    def test_normalized_doc_count(self, evidence_result):
        assert len(evidence_result["normalized_docs"]) == 3

    def test_normalized_doc_field_types(self, evidence_result):
        doc = evidence_result["normalized_docs"][0]
        assert isinstance(doc, NormalizedDocument)
        assert isinstance(doc.doc_id, str) and len(doc.doc_id) == 24
        assert isinstance(doc.source_ref, SourceRef)
        assert isinstance(doc.fingerprint, str)

    def test_normalized_doc_metadata_carried_forward(self, evidence_result):
        doc = evidence_result["normalized_docs"][0]
        assert doc.source_id == "openai_news"
        assert doc.origin_type == "newsroom"
        assert doc.canonical_url == "https://openai.com/news/gpt5"
        assert doc.page_type == "article"
        assert doc.language == "en"
        assert doc.discovery_channels == ["rss", "sitemap"]

    def test_normalized_doc_datetime_parsing(self, evidence_result):
        doc = evidence_result["normalized_docs"][0]
        assert doc.published_at is not None
        assert doc.published_at.year == 2026
        assert doc.published_at.month == 4
        assert doc.published_at.day == 10

        assert doc.updated_at is not None
        assert doc.updated_at.day == 11

    def test_normalized_doc_bad_date_becomes_none(self, evidence_result):
        social_doc = evidence_result["normalized_docs"][2]
        assert social_doc.published_at is None

    def test_normalized_doc_empty_text_handled(self, evidence_result):
        empty_doc = evidence_result["normalized_docs"][1]
        assert empty_doc.body_text == ""
        assert empty_doc.fingerprint is not None

    def test_normalized_doc_missing_metadata_defaults(self, evidence_result):
        empty_doc = evidence_result["normalized_docs"][1]
        assert empty_doc.origin_type == "unknown"
        assert empty_doc.discovery_channels == []
        assert empty_doc.page_type is None
        assert empty_doc.language is None

    def test_evidence_item_structure(self, evidence_result):
        evi = evidence_result["evidence_items"][0]
        assert isinstance(evi, EvidenceItem)
        assert hasattr(evi, "evidence_id")
        assert evi.evidence_id.startswith("evi_")
        assert hasattr(evi, "doc_id")
        assert hasattr(evi, "source_id")
        assert hasattr(evi, "source_trace")
        assert hasattr(evi, "text")

    def test_evidence_item_source_trace(self, evidence_result):
        evi = evidence_result["evidence_items"][0]
        trace = evi.source_trace
        assert trace["provider_id"] == "official:openai_news"
        assert trace["external_id"] == "https://openai.com/news/gpt5"
        assert trace["discovery_channels"] == ["rss", "sitemap"]

    def test_evidence_item_text_truncation(self, evidence_result):
        for evi in evidence_result["evidence_items"]:
            assert len(evi.text) <= 4000

    def test_evidence_metadata_stats(self, evidence_result):
        meta = evidence_result["evidence_metadata"]
        assert meta["raw_batches"] == 2
        assert meta["normalized_docs"] == 3

    def test_doc_id_is_deterministic(self):
        r1 = build_evidence({"raw_batches": _rich_raw_batches()})
        r2 = build_evidence({"raw_batches": _rich_raw_batches()})
        ids1 = [d.doc_id for d in r1["normalized_docs"]]
        ids2 = [d.doc_id for d in r2["normalized_docs"]]
        assert ids1 == ids2


# ===========================================================================
# Layer 3: Events normalization
# ===========================================================================

class TestLayer3EventsNormalization:
    """Verify run_events produces correctly structured events."""

    @pytest.fixture
    def events_result(self) -> dict[str, Any]:
        evi = build_evidence({"raw_batches": _rich_raw_batches()})
        return run_events(evi)

    def test_event_count_matches_evidence(self, events_result):
        assert len(events_result["events"]) == 3

    def test_event_fields_present(self, events_result):
        for evt in events_result["events"]:
            assert isinstance(evt, EventItem)
            assert hasattr(evt, "event_id")
            assert hasattr(evt, "title")
            assert hasattr(evt, "source_id")
            assert hasattr(evt, "supporting_evidence_ids")
            assert isinstance(evt.supporting_evidence_ids, list)
            assert len(evt.supporting_evidence_ids) == 1

    def test_event_title_from_text(self, events_result):
        evt = events_result["events"][0]
        assert "GPT-5" in evt.title or "openai" in evt.title.lower()

    def test_event_evidence_link_fields(self, events_result):
        for link in events_result["event_evidence_links"]:
            assert isinstance(link, EventEvidenceLink)
            assert hasattr(link, "link_id")
            assert hasattr(link, "event_id")
            assert hasattr(link, "evidence_id")
            assert hasattr(link, "support_strength")
            assert isinstance(link.support_strength, float)

    def test_events_metadata(self, events_result):
        meta = events_result["events_metadata"]
        assert meta["event_count"] == 3
        assert meta["link_count"] == 3


# ===========================================================================
# Layer 4: Intelligence normalization
# ===========================================================================

class TestLayer4IntelligenceNormalization:
    """Verify run_intelligence produces correctly structured outputs."""

    @pytest.fixture
    def intel_result(self) -> dict[str, Any]:
        evi = build_evidence({"raw_batches": _rich_raw_batches()})
        events = run_events(evi)
        return run_intelligence(events)

    def test_trend_fields(self, intel_result):
        for t in intel_result["trends"]:
            assert isinstance(t, TrendSignal)
            assert hasattr(t, "trend_id")
            assert hasattr(t, "title")
            assert hasattr(t, "display_title")
            assert hasattr(t, "summary")
            assert hasattr(t, "subject")
            assert hasattr(t, "theme")
            assert hasattr(t, "trend_type")
            assert hasattr(t, "strength_score")
            assert hasattr(t, "novelty_score")
            assert hasattr(t, "corroboration_score")
            assert hasattr(t, "supporting_event_ids")
            assert isinstance(t.strength_score, (int, float))
            assert isinstance(t.corroboration_score, (int, float))
            assert 0.0 <= t.novelty_score <= 1.0
            assert 0.0 <= t.corroboration_score <= 1.0
            assert t.display_title
            assert t.summary
            assert isinstance(t.metadata, dict)
            assert isinstance(t.metadata.get("explain", []), list)

    def test_finding_fields(self, intel_result):
        for f in intel_result["findings"]:
            assert isinstance(f, Finding)
            assert hasattr(f, "finding_id")
            assert hasattr(f, "trend_id")
            assert hasattr(f, "finding_type")
            assert hasattr(f, "title")
            assert hasattr(f, "display_title")
            assert hasattr(f, "summary")
            assert hasattr(f, "importance_score")
            assert hasattr(f, "decision_relevance_score")
            assert hasattr(f, "supporting_event_ids")
            assert hasattr(f, "supporting_evidence_ids")
            assert 0.0 < f.importance_score <= 1.0
            assert 0.0 < f.decision_relevance_score <= 1.0
            assert f.title
            assert f.summary
            assert isinstance(f.metadata, dict)
            assert isinstance(f.metadata.get("explain", []), list)

        scores = [f.importance_score for f in intel_result["findings"]]
        assert len(set(scores)) > 1, "importance should vary across findings for this fixture"

    def test_findings_have_routing_explain(self, intel_result):
        for finding in intel_result["findings"]:
            explain = finding.metadata.get("explain", [])
            assert explain, "finding routing should provide explain text"

    def test_trends_have_merge_explain(self, intel_result):
        for trend in intel_result["trends"]:
            explain = trend.metadata.get("explain", [])
            assert explain, "trend output should explain grouping / significance"

    def test_story_events_merge_into_single_trend(self):
        from tide_watch.models.pipeline import EventItem

        state = {
            "events": [
                EventItem(
                    event_id="evt_story_1",
                    title="OpenAI rolls out enterprise controls for ChatGPT",
                    source_id="openai_news",
                    supporting_evidence_ids=["evi_story_1"],
                ),
                {
                    "event_id": "evt_story_2",
                    "title": "ChatGPT enterprise controls rollout reaches API customers",
                    "source_id": "openai_blog",
                    "event_type": "adoption_event",
                    "subject": "OpenAI",
                    "event_time": "2026-04-14T12:30:00+00:00",
                    "significance_score": 0.72,
                    "confidence": 0.61,
                    "supporting_evidence_ids": ["evi_story_2"],
                    "metadata": {
                        "topic_hits": ["ai_companies:model_release"],
                        "summary": "Same rollout story from another source",
                    },
                },
            ],
            "evidence_items": [
                {"evidence_id": "evi_story_1", "doc_id": "doc_story_1", "source_id": "openai_news", "text": "OpenAI launches enterprise controls."},
                {"evidence_id": "evi_story_2", "doc_id": "doc_story_2", "source_id": "openai_blog", "text": "API customers get the same rollout."},
            ],
            "normalized_docs": [
                {"doc_id": "doc_story_1", "source_id": "openai_news", "title": "OpenAI enterprise controls", "canonical_url": "https://openai.com/news/enterprise-controls", "raw_metadata": {"company": "OpenAI"}},
                {"doc_id": "doc_story_2", "source_id": "openai_blog", "title": "ChatGPT enterprise controls rollout", "canonical_url": "https://openai.com/blog/enterprise-controls", "raw_metadata": {"company": "OpenAI"}},
            ],
        }

        intel = run_intelligence(state)
        assert len(intel["trends"]) == 1
        trend = intel["trends"][0]
        assert sorted(trend.supporting_event_ids) == ["evt_story_1", "evt_story_2"]
        assert trend.metadata.get("merge_reasons")
        assert trend.trend_type in {"adoption_cluster", "momentum_cluster"}
        assert trend.summary

    def test_finding_routing_distinguishes_signal_types(self):
        scenarios = [
            (
                {
                    "event_id": "evt_risk",
                    "title": "OpenAI outage triggers enterprise incident response",
                    "source_id": "openai_status",
                    "event_type": "risk_event",
                    "subject": "OpenAI",
                    "significance_score": 0.84,
                    "confidence": 0.7,
                    "supporting_evidence_ids": ["evi_risk"],
                    "metadata": {
                        "topic_hits": ["ai_companies:risk"],
                        "risk_keyword_hits": ["outage", "incident"],
                    },
                },
                "risk_signal",
            ),
            (
                {
                    "event_id": "evt_opp",
                    "title": "Anthropic expands cloud partnership for enterprise distribution",
                    "source_id": "anthropic_news",
                    "event_type": "opportunity_event",
                    "subject": "Anthropic",
                    "significance_score": 0.76,
                    "confidence": 0.66,
                    "supporting_evidence_ids": ["evi_opp"],
                    "metadata": {
                        "topic_hits": ["ai_companies:opportunity"],
                        "opportunity_keyword_hits": ["partnership"],
                    },
                },
                "opportunity_signal",
            ),
            (
                {
                    "event_id": "evt_comp",
                    "title": "GPT-5 vs Claude benchmark comparison shifts leaderboard discussion",
                    "source_id": "reddit_local_llm",
                    "event_type": "competition_event",
                    "subject": "OpenAI",
                    "significance_score": 0.69,
                    "confidence": 0.6,
                    "supporting_evidence_ids": ["evi_comp"],
                    "metadata": {
                        "watchlist_hits": ["ai_companies:OpenAI", "ai_companies:Anthropic"],
                    },
                },
                "competition_signal",
            ),
            (
                {
                    "event_id": "evt_adopt",
                    "title": "Mistral launches API availability for enterprise customers",
                    "source_id": "mistral_changelog",
                    "event_type": "adoption_event",
                    "subject": "Mistral",
                    "significance_score": 0.67,
                    "confidence": 0.61,
                    "supporting_evidence_ids": ["evi_adopt"],
                    "metadata": {
                        "topic_hits": ["ai_companies:model_release"],
                    },
                },
                "adoption_signal",
            ),
            (
                {
                    "event_id": "evt_narrative",
                    "title": "Media coverage shifts toward frontier model governance",
                    "source_id": "search_newsapi",
                    "event_type": "research_publication",
                    "subject": "Model governance",
                    "significance_score": 0.58,
                    "confidence": 0.56,
                    "supporting_evidence_ids": ["evi_narrative"],
                },
                "narrative_shift",
            ),
        ]

        for event, expected_type in scenarios:
            state = {"events": [event], "evidence_items": [], "normalized_docs": []}
            intel = run_intelligence(state)
            assert len(intel["findings"]) == 1
            finding = intel["findings"][0]
            assert finding.finding_type == expected_type
            assert finding.metadata.get("explain"), f"{expected_type} should include explain"

    def test_alert_fields(self, intel_result):
        alerts = intel_result["alerts"]
        assert len(alerts) >= 1
        finding_ids = {a.finding_id for a in alerts}
        assert len(finding_ids) >= 2, "alerts should attach to more than one finding when eligible"
        for a in alerts:
            assert isinstance(a, AlertItem)
            assert hasattr(a, "alert_id")
            assert hasattr(a, "finding_id")
            assert hasattr(a, "level")

    def test_briefing_fields(self, intel_result):
        assert len(intel_result["briefing_items"]) >= 1
        for b in intel_result["briefing_items"]:
            assert isinstance(b, BriefingItem)
            assert hasattr(b, "briefing_id")
            assert hasattr(b, "finding_id")
            assert hasattr(b, "title")

    def test_intelligence_metadata(self, intel_result):
        meta = intel_result["intelligence_metadata"]
        assert "trends" in meta
        assert "findings" in meta
        assert "alerts" in meta
        assert "briefing_items" in meta


# ===========================================================================
# Layer 5: Decision support normalization
# ===========================================================================

class TestLayer5DecisionSupportNormalization:
    """Verify run_decision_support produces correctly structured outputs."""

    @pytest.fixture
    def decision_result(self) -> dict[str, Any]:
        evi = build_evidence({"raw_batches": _rich_raw_batches()})
        events = run_events(evi)
        intel = run_intelligence(events)
        return run_decision_support(intel)

    def test_signal_fields(self, decision_result):
        for sig in decision_result["decision_signals"]:
            assert isinstance(sig, DecisionSignal)
            assert hasattr(sig, "signal_id")
            assert hasattr(sig, "finding_id")
            assert hasattr(sig, "signal_type")
            assert hasattr(sig, "decision_relevance_score")
            assert hasattr(sig, "supporting_finding_ids")
            assert hasattr(sig, "supporting_event_ids")
            assert hasattr(sig, "supporting_evidence_ids")
            assert isinstance(sig.decision_relevance_score, (int, float))

    def test_recommendation_fields(self, decision_result):
        for rec in decision_result["recommendation_items"]:
            assert isinstance(rec, RecommendationItem)
            assert hasattr(rec, "recommendation_id")
            assert hasattr(rec, "signal_id")
            assert hasattr(rec, "recommended_action")
            assert hasattr(rec, "priority")
            assert isinstance(rec.priority, (int, float))

    def test_brief_fields(self, decision_result):
        assert len(decision_result["decision_briefs"]) >= 1
        for b in decision_result["decision_briefs"]:
            assert isinstance(b, DecisionBrief)
            assert hasattr(b, "brief_id")
            assert hasattr(b, "brief_type")
            assert hasattr(b, "title")
            assert hasattr(b, "key_signals")
            assert hasattr(b, "recommendations")

    def test_decision_support_metadata(self, decision_result):
        meta = decision_result["decision_support_metadata"]
        assert "signals" in meta
        assert "recommendations" in meta
        assert "briefs" in meta


# ===========================================================================
# Storage: IngestionRepository round-trip tests
# ===========================================================================

class TestStorageRoundTrip:
    """Verify data survives write → read cycles without corruption."""

    @pytest.fixture
    def repo(self, tmp_path) -> IngestionRepository:
        return IngestionRepository(str(tmp_path / "roundtrip.sqlite3"))

    def test_document_roundtrip_preserved_fields(self, repo):
        """Verify save_doc persists core columns used by focused ingestion."""
        doc = FocusedNormalizedDocument(
            document_id="rt_doc_001",
            company="OpenAI",
            source_id="openai_news",
            source_type="newsroom",
            url="https://openai.com/news/test",
            canonical_url="https://openai.com/news/test",
            title="Round-Trip Test Article",
            published_at=datetime(2026, 4, 10, 10, 0, tzinfo=timezone.utc),
            updated_at=datetime(2026, 4, 11, 8, 0, tzinfo=timezone.utc),
            ingested_at=NOW,
            doc_type="article",
            content_text="Full article content for round-trip test",
            summary="A test summary",
            tags=["ai", "test"],
            language="en",
            access_mode="direct_html",
            fetch_status=200,
            blocked_by=None,
            quality_score=0.85,
            content_hash="abc123hash",
            raw_metadata={"key": "value", "nested": {"a": 1}},
        )
        repo.save_doc(doc)

        with repo._connect() as conn:
            row = conn.execute(
                "SELECT document_id, source_id, url, title, content_text, "
                "quality_score, raw_metadata FROM normalized_documents "
                "WHERE document_id = ?",
                ("rt_doc_001",),
            ).fetchone()

        assert row is not None
        assert row[0] == "rt_doc_001"
        assert row[1] == "openai_news"
        assert row[2] == "https://openai.com/news/test"
        assert row[3] == "Round-Trip Test Article"
        assert row[4] == "Full article content for round-trip test"
        assert row[5] == 0.85
        meta = json.loads(row[6])
        assert meta["key"] == "value"
        assert meta["nested"]["a"] == 1

    def test_document_all_fields_persist_on_save(self, repo):
        """save_doc writes every FocusedNormalizedDocument column; round-trip matches."""
        doc = FocusedNormalizedDocument(
            document_id="rt_full_001",
            company="Anthropic",
            source_id="anthropic_news",
            source_type="newsroom",
            url="https://anthropic.com/news/test",
            canonical_url="https://anthropic.com/news/canonical",
            title="Full Persist Test",
            published_at=datetime(2026, 4, 10, tzinfo=timezone.utc),
            updated_at=datetime(2026, 4, 12, 15, 30, tzinfo=timezone.utc),
            ingested_at=NOW,
            doc_type="article",
            content_text="Content body",
            summary="Summary text",
            tags=["safety", "policy"],
            language="en",
            access_mode="listing_only",
            fetch_status=200,
            blocked_by=None,
            quality_score=0.9,
            content_hash="hash_xyz",
            raw_metadata={"k": 1},
        )
        repo.save_doc(doc)

        with repo._connect() as conn:
            row = conn.execute(
                """
                SELECT document_id, company, source_id, source_type, url, canonical_url,
                       title, published_at, updated_at, ingested_at, doc_type,
                       content_text, summary, tags, language, access_mode,
                       fetch_status, blocked_by, quality_score, content_hash, raw_metadata
                FROM normalized_documents WHERE document_id = ?
                """,
                ("rt_full_001",),
            ).fetchone()

        assert row is not None
        assert row[0] == doc.document_id
        assert row[1] == doc.company
        assert row[2] == doc.source_id
        assert row[3] == doc.source_type
        assert row[4] == doc.url
        assert row[5] == doc.canonical_url
        assert row[6] == doc.title
        assert row[7] == str(doc.published_at)
        assert row[8] == str(doc.updated_at)
        assert row[9] == str(doc.ingested_at)
        assert row[10] == doc.doc_type
        assert row[11] == doc.content_text
        assert row[12] == doc.summary
        assert json.loads(row[13]) == doc.tags
        assert row[14] == doc.language
        assert row[15] == doc.access_mode
        assert row[16] == doc.fetch_status
        assert row[17] is None
        assert row[18] == doc.quality_score
        assert row[19] == doc.content_hash
        assert json.loads(row[20]) == doc.raw_metadata

    def test_fetch_attempt_roundtrip(self, repo):
        attempt = FetchAttempt(
            source_id="openai_news",
            url="https://openai.com/news/test",
            status_code=403,
            block_type="cloudflare_challenge",
            fetch_mode="direct_html",
            retryable=False,
            error="Challenge page detected",
            created_at=NOW,
        )
        repo.save_attempt(attempt)

        with repo._connect() as conn:
            row = conn.execute(
                "SELECT source_id, url, status_code, block_type, fetch_mode, "
                "retryable, error, created_at "
                "FROM fetch_attempts WHERE source_id = ?",
                ("openai_news",),
            ).fetchone()

        assert row is not None
        assert row[0] == "openai_news"
        assert row[1] == "https://openai.com/news/test"
        assert row[2] == 403
        assert row[3] == "cloudflare_challenge"
        assert row[4] == "direct_html"
        assert row[5] == 0  # False -> 0
        assert row[6] == "Challenge page detected"
        assert "2026" in row[7]

    def test_source_health_roundtrip(self, repo):
        original = {
            "src_a": SourceHealth(
                source_id="src_a",
                success_rate=0.75,
                total_attempts=20,
                total_successes=15,
                anti_bot_score=0.2,
                preferred_mode="listing_only",
                recommended_mode="listing_only",
                documents_ingested=50,
                detail_fetch_attempts=10,
                detail_fetch_successes=8,
                metadata_fallback_docs=5,
                protected_events=2,
            ),
        }
        repo.save_health(original)
        loaded = repo.load_health()

        assert "src_a" in loaded
        h = loaded["src_a"]
        assert h.source_id == "src_a"
        assert h.success_rate == 0.75
        assert h.total_attempts == 20
        assert h.total_successes == 15
        assert h.anti_bot_score == 0.2
        assert h.preferred_mode == "listing_only"
        assert h.recommended_mode == "listing_only"
        assert h.documents_ingested == 50
        assert h.detail_fetch_attempts == 10
        assert h.detail_fetch_successes == 8
        assert h.metadata_fallback_docs == 5
        assert h.protected_events == 2

    def test_source_health_update_preserves_all_fields(self, repo):
        """Write, update, re-read — all fields should survive."""
        h1 = {"s1": SourceHealth(source_id="s1", total_attempts=5, total_successes=3)}
        repo.save_health(h1)

        loaded = repo.load_health()
        loaded["s1"].total_attempts = 10
        loaded["s1"].total_successes = 7
        repo.save_health(loaded)

        reloaded = repo.load_health()
        assert reloaded["s1"].total_attempts == 10
        assert reloaded["s1"].total_successes == 7

    def test_multiple_documents_bulk_save_and_query(self, repo):
        for i in range(10):
            doc = FocusedNormalizedDocument(
                document_id=f"bulk_{i:03d}",
                company="TestCo",
                source_id="test_src",
                source_type="blog",
                url=f"https://test.com/article/{i}",
                title=f"Article {i}",
                ingested_at=NOW,
                access_mode="listing_only",
                quality_score=0.5 + i * 0.05,
                content_hash=f"hash_{i}",
                raw_metadata={},
            )
            repo.save_doc(doc)

        with repo._connect() as conn:
            count = conn.execute("SELECT count(*) FROM normalized_documents").fetchone()[0]
            titles = conn.execute(
                "SELECT title FROM normalized_documents ORDER BY document_id"
            ).fetchall()

        assert count == 10
        assert titles[0][0] == "Article 0"
        assert titles[9][0] == "Article 9"


# ===========================================================================
# Storage: Read existing production SQLite databases
# ===========================================================================

class TestExistingDatabaseReadability:
    """Verify that existing SQLite databases can be read correctly."""

    INGESTION_DB = "data/ingestion.sqlite3"
    REAL_RUN_DB = "data/real_network_run.sqlite"

    @pytest.fixture
    def ingestion_conn(self):
        import os
        db_path = os.path.join(os.path.dirname(__file__), "..", self.INGESTION_DB)
        if not os.path.exists(db_path):
            pytest.skip("ingestion.sqlite3 not available")
        conn = sqlite3.connect(db_path)
        yield conn
        conn.close()

    @pytest.fixture
    def realrun_conn(self):
        import os
        db_path = os.path.join(os.path.dirname(__file__), "..", self.REAL_RUN_DB)
        if not os.path.exists(db_path):
            pytest.skip("real_network_run.sqlite not available")
        conn = sqlite3.connect(db_path)
        yield conn
        conn.close()

    # --- ingestion.sqlite3 ---

    def test_ingestion_tables_exist(self, ingestion_conn):
        tables = {
            r[0]
            for r in ingestion_conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        assert "normalized_documents" in tables
        assert "fetch_attempts" in tables
        assert "source_health" in tables

    def test_ingestion_documents_readable(self, ingestion_conn):
        rows = ingestion_conn.execute(
            "SELECT document_id, source_id, url, title, quality_score "
            "FROM normalized_documents LIMIT 5"
        ).fetchall()
        assert len(rows) > 0
        for row in rows:
            assert row[0] is not None  # document_id
            assert row[1] is not None  # source_id

    def test_ingestion_fetch_attempts_readable(self, ingestion_conn):
        rows = ingestion_conn.execute(
            "SELECT source_id, url, status_code, block_type, created_at "
            "FROM fetch_attempts LIMIT 5"
        ).fetchall()
        assert len(rows) > 0

    def test_ingestion_source_health_deserializable(self, ingestion_conn):
        rows = ingestion_conn.execute(
            "SELECT source_id, payload FROM source_health LIMIT 5"
        ).fetchall()
        assert len(rows) > 0
        for source_id, payload in rows:
            assert source_id is not None
            data = json.loads(payload)
            assert "source_id" in data
            assert "total_attempts" in data
            if hasattr(SourceHealth, "model_validate"):
                h = SourceHealth.model_validate(data)
            else:
                h = SourceHealth.parse_obj(data)
            assert h.source_id == source_id

    def test_ingestion_documents_with_full_fields(self, ingestion_conn):
        """Check documents that have all columns populated (from earlier full INSERT)."""
        rows = ingestion_conn.execute(
            "SELECT document_id, company, source_type, canonical_url, "
            "content_hash, access_mode, ingested_at "
            "FROM normalized_documents "
            "WHERE company IS NOT NULL LIMIT 5"
        ).fetchall()
        for row in rows:
            assert row[1] is not None  # company
            assert row[2] is not None  # source_type
            assert row[4] is not None  # content_hash
            assert row[5] is not None  # access_mode

    def test_ingestion_documents_with_partial_fields(self, ingestion_conn):
        """Legacy rows from older save_doc that omitted columns may still exist."""
        count = ingestion_conn.execute(
            "SELECT count(*) FROM normalized_documents WHERE company IS NULL"
        ).fetchone()[0]
        if count == 0:
            pytest.skip("No partial documents found")
        row = ingestion_conn.execute(
            "SELECT document_id, company, content_hash, access_mode "
            "FROM normalized_documents WHERE company IS NULL LIMIT 1"
        ).fetchone()
        assert row[0] is not None  # document_id always present
        assert row[1] is None  # company lost
        assert row[2] is None  # content_hash lost
        assert row[3] is None  # access_mode lost

    # --- real_network_run.sqlite ---

    def test_realrun_tables_exist(self, realrun_conn):
        tables = {
            r[0]
            for r in realrun_conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        expected = {
            "pipeline_runs", "source_runs", "documents",
            "evidence_items", "events", "event_evidence_links",
            "trend_signals", "intelligence_findings",
            "alert_items", "briefing_items",
            "decision_signals", "recommendation_items", "decision_briefs",
            "source_health", "watchlists", "watchlist_entities", "watchlist_topics",
        }
        for t in expected:
            assert t in tables, f"Table '{t}' missing from real_network_run.sqlite"

    def test_realrun_pipeline_runs_readable(self, realrun_conn):
        rows = realrun_conn.execute(
            "SELECT run_id, status, started_at, finished_at FROM pipeline_runs"
        ).fetchall()
        assert len(rows) >= 1
        for row in rows:
            assert row[0] is not None
            assert row[1] in ("completed", "running", "failed")

    def test_realrun_documents_readable(self, realrun_conn):
        rows = realrun_conn.execute(
            "SELECT run_id, document_id, title, canonical_url, doc_json "
            "FROM documents LIMIT 5"
        ).fetchall()
        assert len(rows) > 0
        for row in rows:
            doc_json = json.loads(row[4])
            assert isinstance(doc_json, dict)

    def test_realrun_evidence_readable(self, realrun_conn):
        rows = realrun_conn.execute(
            "SELECT run_id, evidence_id, document_id, item_json, source_trace_json "
            "FROM evidence_items LIMIT 5"
        ).fetchall()
        assert len(rows) > 0
        for row in rows:
            item = json.loads(row[3])
            trace = json.loads(row[4])
            assert isinstance(item, dict)
            assert isinstance(trace, dict)

    def test_realrun_events_readable(self, realrun_conn):
        rows = realrun_conn.execute(
            "SELECT run_id, event_id, event_type, significance_score, event_json "
            "FROM events LIMIT 5"
        ).fetchall()
        assert len(rows) > 0
        for row in rows:
            event = json.loads(row[4])
            assert isinstance(event, dict)

    def test_realrun_trends_readable(self, realrun_conn):
        rows = realrun_conn.execute(
            "SELECT run_id, trend_id, trend_json FROM trend_signals LIMIT 5"
        ).fetchall()
        assert len(rows) > 0
        for row in rows:
            trend = json.loads(row[2])
            assert isinstance(trend, dict)

    def test_realrun_findings_readable(self, realrun_conn):
        rows = realrun_conn.execute(
            "SELECT run_id, finding_id, finding_type, finding_json "
            "FROM intelligence_findings LIMIT 5"
        ).fetchall()
        assert len(rows) > 0
        for row in rows:
            finding = json.loads(row[3])
            assert isinstance(finding, dict)

    def test_realrun_decision_signals_readable(self, realrun_conn):
        rows = realrun_conn.execute(
            "SELECT run_id, signal_id, finding_id, signal_json "
            "FROM decision_signals LIMIT 5"
        ).fetchall()
        assert len(rows) > 0
        for row in rows:
            signal = json.loads(row[3])
            assert isinstance(signal, dict)

    def test_realrun_recommendations_readable(self, realrun_conn):
        rows = realrun_conn.execute(
            "SELECT run_id, recommendation_id, signal_id, recommended_action, rec_json "
            "FROM recommendation_items LIMIT 5"
        ).fetchall()
        assert len(rows) > 0
        for row in rows:
            rec = json.loads(row[4])
            assert isinstance(rec, dict)

    def test_realrun_cross_layer_traceability(self, realrun_conn):
        """Walk the full chain: decision_signal → finding → event → evidence → document."""
        sig = realrun_conn.execute(
            "SELECT signal_id, finding_id, signal_json FROM decision_signals LIMIT 1"
        ).fetchone()
        if sig is None:
            pytest.skip("No decision signals")
        signal_data = json.loads(sig[2])
        finding_id = sig[1]

        finding = realrun_conn.execute(
            "SELECT finding_id, finding_json FROM intelligence_findings "
            "WHERE finding_id = ?",
            (finding_id,),
        ).fetchone()
        assert finding is not None, f"Finding {finding_id} not found"
        finding_data = json.loads(finding[1])

        event_ids = finding_data.get("supporting_event_ids", [])
        if event_ids:
            event = realrun_conn.execute(
                "SELECT event_id, event_json FROM events WHERE event_id = ?",
                (event_ids[0],),
            ).fetchone()
            assert event is not None

        evidence_links = realrun_conn.execute(
            "SELECT evidence_id FROM event_evidence_links WHERE event_id = ?",
            (event_ids[0],) if event_ids else ("",),
        ).fetchall()
        if evidence_links:
            evi = realrun_conn.execute(
                "SELECT evidence_id, document_id FROM evidence_items "
                "WHERE evidence_id = ?",
                (evidence_links[0][0],),
            ).fetchone()
            if evi:
                doc = realrun_conn.execute(
                    "SELECT document_id, title FROM documents "
                    "WHERE document_id = ?",
                    (evi[1],),
                ).fetchone()
                assert doc is not None, (
                    f"Document {evi[1]} referenced by evidence not found"
                )
