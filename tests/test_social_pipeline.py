"""Social pipeline：配置、connector、enrich、normalize、ranking、metadata fallback。"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from textwrap import dedent

from tide_watch.models.graph_state import TideWatchState
from tide_watch.nodes.normalize import node_normalize_batch
from tide_watch.sources.social.config_loader import load_social_registry
from tide_watch.sources.social.connectors.hackernews import HackerNewsConnector
from tide_watch.sources.social.connectors.reddit import RedditConnector
from tide_watch.sources.social.connectors.x import XConnector
from tide_watch.sources.social.models import SocialCandidateItem, SocialSourceConfig
from tide_watch.sources.social.normalizers import metadata_fallback_batch
from tide_watch.sources.social.pipeline import collect_social_batches
from tide_watch.sources.social.ranking import compute_quality_score, engagement_score_from_signals


def test_social_sources_load_from_yaml(tmp_path: Path):
    p = tmp_path / "s.yaml"
    p.write_text(
        dedent(
            """
            social_sources:
              - source_id: s1
                platform: reddit
                source_type: subreddit_feed
                handle_or_community: test
                enabled: true
                max_items: 5
            """
        ),
        encoding="utf-8",
    )
    reg = load_social_registry(p)
    assert len(reg.social_sources) == 1
    assert reg.social_sources[0].source_id == "s1"


def test_reddit_discover_maps_to_candidates(monkeypatch):
    now = datetime.now(timezone.utc)
    payload = {
        "data": {
            "children": [
                {
                    "kind": "t3",
                    "data": {
                        "id": "abc123",
                        "title": "Hello",
                        "selftext": "Body",
                        "permalink": "/r/test/comments/abc123/hello/",
                        "author": "u1",
                        "created_utc": now.timestamp(),
                        "score": 10,
                        "num_comments": 3,
                        "subreddit": "test",
                    },
                }
            ],
            "after": None,
        }
    }

    monkeypatch.setattr(
        "tide_watch.sources.social.connectors.reddit.http_get_json",
        lambda *a, **k: payload,
    )
    src = SocialSourceConfig(
        source_id="r1",
        platform="reddit",
        source_type="subreddit_feed",
        handle_or_community="test",
        max_items=5,
    )
    conn = RedditConnector()
    cands, cp = conn.discover(src, None)
    assert len(cands) == 1
    assert cands[0].external_id == "t3_abc123"
    assert "reddit.com" in cands[0].url
    assert cands[0].title == "Hello"
    assert cp is not None


def test_hackernews_discover_search(monkeypatch):
    payload = {
        "hits": [
            {
                "objectID": "999",
                "title": "AI post",
                "url": "https://example.com/a",
                "author": "bob",
                "points": 42,
                "num_comments": 7,
                "created_at_i": 1700000000,
            }
        ]
    }
    monkeypatch.setattr(
        "tide_watch.sources.social.connectors.hackernews.http_get_json",
        lambda *a, **k: payload,
    )
    src = SocialSourceConfig(
        source_id="hn1",
        platform="hackernews",
        source_type="search",
        query="ai",
        max_items=5,
    )
    conn = HackerNewsConnector()
    cands, _cp = conn.discover(src, None)
    assert len(cands) == 1
    assert cands[0].external_id == "999"
    assert cands[0].engagement.get("points") == 42


def test_reddit_enrich_includes_comments(monkeypatch):
    src = SocialSourceConfig(
        source_id="r1",
        platform="reddit",
        source_type="subreddit_feed",
        handle_or_community="x",
        include_comments=True,
        max_items=3,
    )
    item = SocialCandidateItem(
        source_id="r1",
        platform="reddit",
        source_type="subreddit_feed",
        external_id="t3_pid",
        url="https://www.reddit.com/r/x/comments/pid/",
        title="T",
        text="main",
        discovered_at=datetime.now(timezone.utc),
        engagement={},
    )

    def fake_get(url, **kwargs):
        if "/comments/pid" in url:
            return [
                {"data": {"children": [{"kind": "t3", "data": {"id": "pid", "title": "T", "selftext": "main"}}]}},
                {
                    "data": {
                        "children": [
                            {
                                "kind": "t1",
                                "data": {"body": "c1", "author": "a1"},
                            }
                        ]
                    }
                },
            ]
        raise AssertionError(url)

    monkeypatch.setattr("tide_watch.sources.social.connectors.reddit.http_get_json", fake_get)
    batch = RedditConnector().enrich([item], src, None)
    assert len(batch.records) == 1
    assert "comments" in (batch.records[0].text or "")


def test_hn_enrich_story_and_comments(monkeypatch):
    src = SocialSourceConfig(
        source_id="hn1",
        platform="hackernews",
        source_type="top_feed",
        include_comments=True,
        max_items=2,
    )
    item = SocialCandidateItem(
        source_id="hn1",
        platform="hackernews",
        source_type="top_feed",
        external_id="1",
        url="https://news.ycombinator.com/item?id=1",
        title="Story",
        text="",
        discovered_at=datetime.now(timezone.utc),
        engagement={},
        metadata={"kids": [2]},
    )

    def fake_get(url, **kwargs):
        if url.endswith("/item/1.json"):
            return {
                "type": "story",
                "title": "Story",
                "score": 5,
                "descendants": 1,
                "text": "<p>Hi</p>",
                "time": 1700000000,
                "kids": [2],
            }
        if url.endswith("/item/2.json"):
            return {"type": "comment", "by": "u", "text": "reply"}
        raise AssertionError(url)

    monkeypatch.setattr("tide_watch.sources.social.connectors.hackernews.http_get_json", fake_get)
    batch = HackerNewsConnector().enrich([item], src, None)
    assert batch.records
    assert "reply" in (batch.records[0].text or "")


def test_normalize_social_metadata_published_at():
    from tide_watch.models.ids import SourceRef
    from tide_watch.models.raw import RawFetchBatch, RawRecord

    pub = datetime(2024, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
    rec = RawRecord(
        source_ref=SourceRef(provider_id="social:t", external_id="e1"),
        fetched_at=datetime.now(timezone.utc),
        text="x",
        metadata={"title": "T", "url": "https://u", "published_at": pub.isoformat()},
        idempotency_key="k",
    )
    state: TideWatchState = {"raw_batches": [RawFetchBatch(batch_id="b", records=[rec])]}
    out = node_normalize_batch(state)
    docs = out["normalized_docs"]
    assert docs[0].published_at == pub


def test_ranking_scores():
    item = SocialCandidateItem(
        source_id="s",
        platform="reddit",
        source_type="x",
        external_id="1",
        url="https://x",
        title="A" * 20,
        text="Discussion about https://example.com and more text here",
        discovered_at=datetime.now(timezone.utc),
        engagement={"score": 100, "num_comments": 20},
    )
    eng = engagement_score_from_signals(item.engagement, "reddit")
    assert 0 <= eng <= 1
    q = compute_quality_score(
        item,
        content_text=item.text,
        trust_tier=3,
        has_comment_context=True,
        metadata_only=False,
    )
    assert 0 <= q <= 1


def test_metadata_fallback_batch():
    src = SocialSourceConfig(
        source_id="s",
        platform="reddit",
        source_type="search",
        query="q",
        enabled=True,
    )
    c = SocialCandidateItem(
        source_id="s",
        platform="reddit",
        source_type="search",
        external_id="t3_z",
        url="https://reddit.com",
        title="Only title",
        text="",
        discovered_at=datetime.now(timezone.utc),
        engagement={},
    )
    batch = metadata_fallback_batch([c], src, batch_id="fb1")
    assert batch.records
    assert batch.records[0].metadata.get("metadata_fallback") is True


def test_pipeline_runs_with_mocks(tmp_path: Path, monkeypatch):
    p = tmp_path / "cfg.yaml"
    p.write_text(
        dedent(
            """
            social_sources:
              - source_id: r_test
                platform: reddit
                source_type: subreddit_feed
                handle_or_community: x
                enabled: true
                max_items: 2
                include_comments: false
              - source_id: x_stub
                platform: x
                source_type: account_feed
                handle_or_community: OpenAI
                enabled: true
            """
        ),
        encoding="utf-8",
    )

    def reddit_json(url, **kwargs):
        return {
            "data": {
                "children": [
                    {
                        "kind": "t3",
                        "data": {
                            "id": "aa",
                            "title": "t",
                            "selftext": "",
                            "permalink": "/r/x/comments/aa/a/",
                            "author": "u",
                            "created_utc": 1700000000.0,
                            "score": 1,
                            "num_comments": 0,
                        },
                    }
                ],
                "after": None,
            }
        }

    monkeypatch.setattr("tide_watch.sources.social.connectors.reddit.http_get_json", reddit_json)
    scope: dict = {}
    batches, errors, _health = collect_social_batches(config_path=str(p), scope=scope, run_id="t1")
    assert any(len(b.records) > 0 for b in batches)
    assert "social_checkpoints" in scope
    assert "r_test" in scope["social_checkpoints"]
    assert any("x: pending" in e or "pending_official_api" in e for e in errors) or any(
        "x:" in e for e in errors
    )


def test_x_connector_pending():
    src = SocialSourceConfig(
        source_id="x1",
        platform="x",
        source_type="account_feed",
        handle_or_community="a",
        enabled=True,
    )
    cands, _ = XConnector().discover(src, None)
    assert cands == []
    batch = XConnector().enrich([], src, None)
    assert batch.errors
