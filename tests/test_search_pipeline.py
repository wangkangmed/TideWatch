from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
from textwrap import dedent

from tide_watch.models.ids import SourceRef
from tide_watch.models.raw import RawFetchBatch, RawRecord
from tide_watch.nodes.collect import node_collect_search
from tide_watch.models.ingestion import FetchResult
from tide_watch.sources.search.connectors.newsapi import NewsApiConnector
from tide_watch.sources.search.enrichment.fetch_bridge import build_fetch_plans, fetch_candidates_to_raw_batch
from tide_watch.sources.search.models import (
    RankedSearchCandidate,
    SearchCandidate,
    SearchMonitorConfig,
    SearchProviderConfig,
    SearchQuery,
    SearchResultItem,
)
from tide_watch.sources.search.pipeline import run_search_discovery
from tide_watch.sources.search.processing import guess_origin_type, merge_results_to_candidates, rank_and_route
from tide_watch.sources.search.query.builder import build_queries_for_monitor


def test_query_builder_from_templates():
    monitor = SearchMonitorConfig(
        monitor_id="m1",
        topic="OpenAI",
        query_templates=["brand_updates", "brand_risk"],
        risk_terms=["outage", "lawsuit"],
    )
    queries = build_queries_for_monitor(monitor)
    assert len(queries) >= 2
    assert all(q.monitor_id == "m1" for q in queries)
    assert any("OpenAI" in q.text for q in queries)


def test_newsapi_connector_maps_response(monkeypatch):
    class _Resp:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "articles": [
                    {
                        "url": "https://example.com/a",
                        "title": "A",
                        "description": "desc",
                        "publishedAt": "2026-01-01T00:00:00Z",
                        "source": {"name": "x"},
                    }
                ]
            }

    class _Client:
        def __init__(self, *args, **kwargs):
            _ = (args, kwargs)

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            _ = (exc_type, exc, tb)
            return False

        def get(self, *args, **kwargs):
            _ = (args, kwargs)
            return _Resp()

    monkeypatch.setenv("NEWSAPI_API_KEY", "k")
    monkeypatch.setattr("tide_watch.sources.search.connectors.newsapi.httpx.Client", _Client)
    conn = NewsApiConnector()
    q = SearchQuery(query_id="q1", monitor_id="m", topic_id="t", text="OpenAI")
    cfg = SearchProviderConfig(provider_id="newsapi_main", provider="newsapi", api_key_ref="NEWSAPI_API_KEY")
    out = conn.search(q, cfg)
    assert len(out) == 1
    assert out[0].provider == "newsapi_main"
    assert out[0].domain == "example.com"


def test_dedupe_merge_and_origin_guess():
    qid = "q1"
    items = [
        SearchResultItem.with_domain(query_id=qid, provider="p1", rank=1, url="https://openai.com/news?a=1", title="t1"),
        SearchResultItem.with_domain(query_id="q2", provider="p2", rank=2, url="https://openai.com/news/?a=1", title="t2"),
        SearchResultItem.with_domain(
            query_id="q3", provider="p2", rank=3, url="https://www.reddit.com/r/ai/comments/x", title="t3"
        ),
        SearchResultItem.with_domain(query_id="q4", provider="p2", rank=4, url="https://third.example.org/p", title="t4"),
    ]
    cands = merge_results_to_candidates(items)
    assert len(cands) == 3
    by_domain = {c.domain: c for c in cands}
    guess_origin_type(by_domain["openai.com"], known_official_domains={"openai.com"})
    guess_origin_type(by_domain["www.reddit.com"], known_official_domains={"openai.com"})
    guess_origin_type(by_domain["third.example.org"], known_official_domains={"openai.com"})
    assert by_domain["openai.com"].likely_origin_type == "first_party"
    assert by_domain["www.reddit.com"].likely_origin_type == "community"
    assert by_domain["third.example.org"].likely_origin_type == "external_web"


def test_ranking_and_routing_outputs_explainable_priority():
    now = datetime.now(timezone.utc)
    c = SearchCandidate(
        candidate_id="c1",
        url="https://third.example.org/p",
        canonical_url="https://third.example.org/p",
        title_hint="OpenAI product release details",
        summary_hint="summary",
        published_hint=now - timedelta(days=1),
        domain="third.example.org",
        matched_queries=["q1", "q2"],
        provider_hits=["brave", "newsapi"],
        likely_origin_type="external_web",
    )
    ranked = rank_and_route([c], min_fetch_score=0.1)
    assert ranked[0].route == "route_to_web_fetch"
    assert ranked[0].fetch_priority > 0
    assert any("final_score" in x for x in ranked[0].explain)


def test_fetch_bridge_to_existing_web_fetch(monkeypatch):
    ranked = rank_and_route(
        [
            SearchCandidate(
                candidate_id="c1",
                url="https://external.example.com/a",
                canonical_url="https://external.example.com/a",
                title_hint="A title with enough length",
                domain="external.example.com",
                matched_queries=["q1"],
                provider_hits=["brave"],
                likely_origin_type="external_web",
            )
        ],
        min_fetch_score=0.0,
    )
    plans = build_fetch_plans(ranked)
    assert plans
    monkeypatch.setattr(
        "tide_watch.sources.search.enrichment.fetch_bridge.run_fetch_plan",
        lambda _plan: FetchResult(
            source_id="c1",
            company="search_discovery",
            url="https://external.example.com/a",
            final_url="https://external.example.com/a",
            status_code=200,
            content_type="text/html",
            raw_text="<html>ok</html>",
            success=True,
        ),
    )
    batch = fetch_candidates_to_raw_batch(ranked, batch_id="b1")
    assert len(batch.records) == 1
    assert batch.records[0].metadata.get("search_bridge") is True


def test_search_pipeline_minimal_run_without_llm(tmp_path: Path, monkeypatch):
    p = tmp_path / "cfg.yaml"
    p.write_text(
        dedent(
            """
            companies:
              - company: OpenAI
                sources:
                  - id: openai_news
                    type: newsroom
                    url: https://openai.com/news
            search_providers:
              - provider_id: brave_main
                provider: brave
                enabled: true
                api_key_ref: BRAVE_SEARCH_API_KEY
                default_limit: 10
            search_monitors:
              - monitor_id: m1
                topic: OpenAI
                query_templates: [brand_updates]
                enabled: true
                providers: [brave_main]
                time_window: 7d
            """
        ),
        encoding="utf-8",
    )

    class _FakeConnector:
        def search(self, query, provider_config, checkpoint=None):
            _ = (provider_config, checkpoint)
            return [
                SearchResultItem.with_domain(
                    query_id=query.query_id,
                    provider="brave_main",
                    rank=1,
                    url="https://openai.com/news/new-release",
                    title="Release",
                    snippet="Update",
                ),
                SearchResultItem.with_domain(
                    query_id=query.query_id,
                    provider="brave_main",
                    rank=2,
                    url="https://external.example.org/analysis",
                    title="Analysis",
                    snippet="Trend",
                ),
            ]

    monkeypatch.setattr(
        "tide_watch.sources.search.pipeline.connector_by_provider",
        lambda _provider: _FakeConnector(),
    )
    ranked, raw_results = run_search_discovery(config_path=str(p), top_n=10, min_fetch_score=0.0)
    assert len(raw_results) >= 2
    assert ranked
    assert any(x.candidate.likely_origin_type == "first_party" for x in ranked)


def test_skeleton_provider_connector_interface():
    from tide_watch.sources.search.connectors.exa import ExaSearchConnector

    conn = ExaSearchConnector()
    q = SearchQuery(query_id="q", monitor_id="m", topic_id="t", text="x")
    cfg = SearchProviderConfig(provider_id="exa_main", provider="exa")
    assert conn.search(q, cfg) == []


def test_node_collect_search_integrates_pipeline(monkeypatch):
    ranked = [
        RankedSearchCandidate(
            candidate=SearchCandidate(
                candidate_id="c1",
                url="https://external.example.com/a",
                canonical_url="https://external.example.com/a",
                domain="external.example.com",
                matched_queries=["q1"],
                provider_hits=["newsapi_main"],
                likely_origin_type="external_web",
                title_hint="A title",
            ),
            route="route_to_web_fetch",
            explain=["ok"],
            fetch_priority=80,
        )
    ]
    rec = RawRecord(
        source_ref=SourceRef(provider_id="search:c1", external_id="https://external.example.com/a"),
        fetched_at=datetime.now(timezone.utc),
        mime_type="text/html",
        text="<html>ok</html>",
        metadata={"url": "https://external.example.com/a", "search_bridge": True},
        idempotency_key="k1",
    )
    fake_batch = RawFetchBatch(batch_id="search-test", records=[rec], errors=[])

    monkeypatch.setattr(
        "tide_watch.nodes.collect.run_search_discovery",
        lambda **kwargs: (ranked, []),
    )
    monkeypatch.setattr(
        "tide_watch.nodes.collect.fetch_candidates_to_raw_batch",
        lambda items, batch_id="search-web-fetch": fake_batch,
    )
    out = asyncio.run(node_collect_search({"run_id": "r1", "scope": {}}))
    assert len(out.get("raw_batches") or []) == 1
    assert (out["raw_batches"][0].records[0].metadata or {}).get("search_bridge") is True
    assert (out.get("scope") or {}).get("search_last_run", {}).get("ranked_candidates") == 1


def test_node_collect_search_respects_disable_flag(monkeypatch):
    monkeypatch.setenv("TIDEWATCH_USE_SEARCH_DISCOVERY", "false")
    out = asyncio.run(node_collect_search({"run_id": "r2", "scope": {}}))
    assert out == {}
