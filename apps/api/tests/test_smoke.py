"""Smoke tests – hit every list endpoint and verify 200."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

ENDPOINTS = [
    "/health",
    "/api/v1/overview",
    "/api/v1/trends",
    "/api/v1/findings",
    "/api/v1/recommendations",
    "/api/v1/briefs",
    "/api/v1/briefing-items",
    "/api/v1/alerts",
    "/api/v1/events",
    "/api/v1/watchlists",
    "/api/v1/runs",
]


@pytest.mark.parametrize("path", ENDPOINTS)
def test_endpoint_returns_200(path: str):
    resp = client.get(path)
    assert resp.status_code == 200, f"{path} returned {resp.status_code}: {resp.text}"
