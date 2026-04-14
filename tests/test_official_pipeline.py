"""Official pipeline：多 transport、REST discovery、YAML 兼容、prefer/combine。"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from textwrap import dedent

from tide_watch.focused import models as focused_models
from tide_watch.focused.classifier import classify_fetch_result
from tide_watch.sources.official.config_loader import load_source_config
from tide_watch.sources.official.discovery.api import discover_from_rest_api
from tide_watch.sources.official.discovery.sitemap import discover_from_sitemap
from tide_watch.sources.official.pipeline import collect_official_discovery, resolved_transport_strategies
from tide_watch.sources.official.source_definitions import (
    CandidateURL,
    CompanySourceConfig,
    OfficialTransportConfig,
    SourceDefinition,
    SourceRegistryConfig,
)


def test_focused_models_shim_exports_source_definition():
    src = focused_models.SourceDefinition(id="a", type="t", url="https://example.com")
    assert src.id == "a"


def test_official_sources_top_level_yaml_normalized(tmp_path: Path):
    p = tmp_path / "cfg.yaml"
    p.write_text(
        dedent(
            """
            official_sources:
              - source_id: demo_src
                provider: demo_co
                type: newsroom
                url: https://example.com/news
                strategies:
                  - transport: html_listing
                    enabled: true
                    priority: 10
                    url: https://example.com/news
            """
        ),
        encoding="utf-8",
    )
    cfg = load_source_config(str(p))
    assert len(cfg.companies) == 1
    assert cfg.companies[0].company == "demo_co"
    assert cfg.companies[0].sources[0].id == "demo_src"


def test_resolved_legacy_includes_optional_parallel_transports():
    s = SourceDefinition(
        id="m",
        type="newsroom",
        url="https://example.com/a",
        rss_url="https://example.com/feed.xml",
        sitemap_url="https://example.com/sm.xml",
    )
    names = [x.transport for x in resolved_transport_strategies(s)]
    assert "rss" in names and "sitemap" in names and "html_listing" in names


def test_combine_mode_merges_two_transports(monkeypatch):
    now = datetime.now(timezone.utc)

    def fake_rss(company, source, max_items=30, feed_url=None):
        return [
            CandidateURL(
                source_id=source.id,
                company=company,
                url="https://example.com/u-rss",
                discovered_at=now,
                source_type=source.type,
                metadata={},
            )
        ]

    def fake_listing(company, source, listing_url=None):
        return [
            CandidateURL(
                source_id=source.id,
                company=company,
                url="https://example.com/u-list",
                discovered_at=now,
                source_type=source.type,
                hint_doc_type="listing",
                metadata={"seed": True},
            )
        ]

    monkeypatch.setattr("tide_watch.sources.official.pipeline.discover_from_rss", fake_rss)
    monkeypatch.setattr("tide_watch.sources.official.pipeline.discover_from_listing", fake_listing)

    src = SourceDefinition(
        id="x",
        type="newsroom",
        url="https://example.com/l",
        transport_collection_mode="combine",
        strategies=[
            OfficialTransportConfig(transport="html_listing", url="https://example.com/l", priority=50),
            OfficialTransportConfig(transport="rss", url="https://example.com/f.xml", priority=100),
        ],
    )
    cfg = SourceRegistryConfig(companies=[CompanySourceConfig(company="C", sources=[src])])
    out = collect_official_discovery(cfg, max_candidates=50)
    urls = {c.url for c in out}
    assert "https://example.com/u-rss" in urls
    assert "https://example.com/u-list" in urls


def test_prefer_fallback_skips_second_when_first_nonempty(monkeypatch):
    now = datetime.now(timezone.utc)

    def fake_rss(*_a, **_k):
        return [
            CandidateURL(
                source_id="x",
                company="C",
                url="https://example.com/only-rss",
                discovered_at=now,
                source_type="newsroom",
                metadata={},
            )
        ]

    def fake_listing(*_a, **_k):
        return [
            CandidateURL(
                source_id="x",
                company="C",
                url="https://example.com/never",
                discovered_at=now,
                source_type="newsroom",
                metadata={},
            )
        ]

    monkeypatch.setattr("tide_watch.sources.official.pipeline.discover_from_rss", fake_rss)
    monkeypatch.setattr("tide_watch.sources.official.pipeline.discover_from_listing", fake_listing)

    src = SourceDefinition(
        id="x",
        type="newsroom",
        url="https://example.com/l",
        transport_collection_mode="prefer_fallback",
        strategies=[
            OfficialTransportConfig(transport="rss", url="https://example.com/f.xml", priority=100),
            OfficialTransportConfig(transport="html_listing", url="https://example.com/l", priority=50),
        ],
    )
    cfg = SourceRegistryConfig(companies=[CompanySourceConfig(company="C", sources=[src])])
    out = collect_official_discovery(cfg, max_candidates=50)
    assert len(out) == 1
    assert out[0].url == "https://example.com/only-rss"


def test_sitemap_discovery_returns_candidate_urls(monkeypatch):
    xml = """<?xml version="1.0" encoding="UTF-8"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
      <url><loc>https://example.com/a</loc></url>
    </urlset>"""

    monkeypatch.setattr("tide_watch.sources.official.discovery.sitemap.get_url_text", lambda *a, **k: xml)
    monkeypatch.setattr("tide_watch.sources.official.discovery.sitemap.url_host_resolvable", lambda *_a, **_k: True)

    src = SourceDefinition(id="sm", type="sitemap", url="https://example.com/s.xml", access="feed_only")
    out = discover_from_sitemap("Co", src, max_items=10)
    assert len(out) == 1
    assert out[0].url == "https://example.com/a"


def test_rest_api_maps_list_json(monkeypatch):
    monkeypatch.setattr(
        "tide_watch.sources.official.discovery.api.get_url_text",
        lambda *a, **k: '{"items":[{"url":"https://ex.com/p","title":"Hi","id":"1"}]}',
    )
    monkeypatch.setattr("tide_watch.sources.official.discovery.api.url_host_resolvable", lambda *_a, **_k: True)
    monkeypatch.setattr("tide_watch.sources.official.discovery.api.time.sleep", lambda *_a, **_k: None)
    src = SourceDefinition(id="api1", type="api", url="about:blank", access="api", api_list_url="https://ex.com/list")
    strat = OfficialTransportConfig(transport="rest_api", url="https://ex.com/list", items_path="items")
    out = discover_from_rest_api("Co", src, strat, max_items=10)
    assert len(out) == 1
    assert out[0].url == "https://ex.com/p"
    assert out[0].metadata.get("title") == "Hi"


def test_classify_shim_still_importable():
    from tide_watch.models.ingestion import FetchResult

    r = FetchResult(
        source_id="s",
        company="c",
        url="https://x",
        status_code=200,
        success=True,
    )
    classify_fetch_result(r)


def test_combine_mode_survives_single_transport_failure(monkeypatch):
    now = datetime.now(timezone.utc)

    def boom(*_a, **_k):
        raise RuntimeError("dns failed")

    def ok_listing(company, source, listing_url=None):
        return [
            CandidateURL(
                source_id=source.id,
                company=company,
                url="https://example.com/from-listing",
                discovered_at=now,
                source_type=source.type,
                metadata={"seed": True},
            )
        ]

    monkeypatch.setattr("tide_watch.sources.official.pipeline.discover_from_rss", boom)
    monkeypatch.setattr("tide_watch.sources.official.pipeline.discover_from_listing", ok_listing)
    src = SourceDefinition(
        id="x2",
        type="newsroom",
        url="https://example.com/news",
        transport_collection_mode="combine",
        strategies=[
            OfficialTransportConfig(transport="rss", url="https://example.com/feed.xml", priority=100),
            OfficialTransportConfig(transport="html_listing", url="https://example.com/news", priority=80),
        ],
    )
    cfg = SourceRegistryConfig(companies=[CompanySourceConfig(company="C", sources=[src])])
    out = collect_official_discovery(cfg, max_candidates=20)
    assert any(c.url == "https://example.com/from-listing" for c in out)


def test_collection_mode_rss_only_filters_non_rss(monkeypatch):
    now = datetime.now(timezone.utc)

    def fake_rss(company, source, max_items=30, feed_url=None):
        return [
            CandidateURL(
                source_id=source.id,
                company=company,
                url="https://example.com/rss-item",
                discovered_at=now,
                source_type=source.type,
                metadata={},
            )
        ]

    def fake_listing(company, source, listing_url=None):
        return [
            CandidateURL(
                source_id=source.id,
                company=company,
                url="https://example.com/listing-seed",
                discovered_at=now,
                source_type=source.type,
                metadata={"seed": True},
            )
        ]

    monkeypatch.setattr("tide_watch.sources.official.pipeline.discover_from_rss", fake_rss)
    monkeypatch.setattr("tide_watch.sources.official.pipeline.discover_from_listing", fake_listing)
    src = SourceDefinition(
        id="x3",
        type="newsroom",
        url="https://example.com/news",
        transport_collection_mode="combine",
        strategies=[
            OfficialTransportConfig(transport="rss", url="https://example.com/feed.xml", priority=100),
            OfficialTransportConfig(transport="html_listing", url="https://example.com/news", priority=80),
        ],
    )
    cfg = SourceRegistryConfig(companies=[CompanySourceConfig(company="C", sources=[src])])
    out = collect_official_discovery(cfg, max_candidates=20, collection_mode="rss_only")
    assert len(out) == 1
    assert out[0].url == "https://example.com/rss-item"
