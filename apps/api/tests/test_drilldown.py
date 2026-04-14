"""Drill-down tests – verify detail endpoints return enriched data."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_overview_has_all_sections():
    resp = client.get("/api/v1/overview")
    assert resp.status_code == 200
    data = resp.json()
    assert "counts" in data
    assert "latest_run" in data
    assert "top_trends" in data
    assert "top_findings" in data
    assert "top_recommendations" in data


def test_trends_list_has_pagination():
    resp = client.get("/api/v1/trends")
    data = resp.json()
    assert "items" in data
    assert "pagination" in data
    assert data["pagination"]["total"] >= 0


def test_trend_detail():
    resp = client.get("/api/v1/trends")
    items = resp.json().get("items", [])
    if items:
        tid = items[0]["trend_id"]
        detail = client.get(f"/api/v1/trends/{tid}").json()
        assert "trend_id" in detail
        assert "metadata" in detail


def test_finding_detail_has_drilldown():
    resp = client.get("/api/v1/findings")
    items = resp.json().get("items", [])
    if items:
        fid = items[0]["finding_id"]
        detail = client.get(f"/api/v1/findings/{fid}").json()
        assert "related_events" in detail
        assert "related_evidence" in detail
        assert "related_recommendations" in detail


def test_recommendation_detail_has_signal():
    resp = client.get("/api/v1/recommendations")
    items = resp.json().get("items", [])
    if items:
        rid = items[0]["recommendation_id"]
        detail = client.get(f"/api/v1/recommendations/{rid}").json()
        assert "metadata" in detail


def test_event_detail_has_evidence():
    resp = client.get("/api/v1/events")
    items = resp.json().get("items", [])
    if items:
        eid = items[0]["event_id"]
        detail = client.get(f"/api/v1/events/{eid}").json()
        assert "evidence_items" in detail


def test_brief_detail():
    resp = client.get("/api/v1/briefs")
    items = resp.json().get("items", [])
    if items:
        bid = items[0]["brief_id"]
        detail = client.get(f"/api/v1/briefs/{bid}").json()
        assert "key_signals" in detail
        assert "recommendations" in detail


def test_watchlist_detail():
    resp = client.get("/api/v1/watchlists")
    items = resp.json().get("items", [])
    if items:
        wid = items[0]["watchlist_id"]
        detail = client.get(f"/api/v1/watchlists/{wid}").json()
        assert "entities" in detail
        assert "topics" in detail


def test_run_detail():
    resp = client.get("/api/v1/runs")
    items = resp.json().get("items", [])
    if items:
        rid = items[0]["run_id"]
        detail = client.get(f"/api/v1/runs/{rid}").json()
        assert "metadata" in detail
        assert "document_count" in detail


def test_404_on_missing():
    resp = client.get("/api/v1/trends/nonexistent-id")
    assert resp.status_code == 404
    resp = client.get("/api/v1/findings/nonexistent-id")
    assert resp.status_code == 404
