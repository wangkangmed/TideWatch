from datetime import datetime, timezone

from tide_watch.focused.discovery.listing import discover_from_listing
from tide_watch.focused.discovery.rss import discover_from_rss
from tide_watch.focused.models import SourceDefinition


def test_listing_discovery_returns_candidate():
    source = SourceDefinition(id="s1", type="newsroom", url="https://example.com/news", access="listing_only")
    out = discover_from_listing("Example", source)
    assert len(out) == 1
    assert out[0].source_id == "s1"


def test_rss_discovery_parses_entries(monkeypatch):
    class Resp:
        text = "<rss />"

        def raise_for_status(self):
            return None

    class Parsed:
        entries = [
            type("E", (), {"link": "https://example.com/p1", "title": "t1", "summary": "s1", "published": "now"})()
        ]

    monkeypatch.setattr("tide_watch.sources.official.discovery.rss.httpx.get", lambda *a, **k: Resp())
    monkeypatch.setattr("tide_watch.sources.official.discovery.rss.feedparser.parse", lambda *_: Parsed())
    source = SourceDefinition(id="rss1", type="rss", url="https://example.com/feed.xml", access="feed_only")
    out = discover_from_rss("Example", source, max_items=10)
    assert len(out) == 1
    assert out[0].metadata["title"] == "t1"
