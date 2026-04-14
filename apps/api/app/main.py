"""TideWatch read-only API – serves the analyst dashboard frontend."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import alerts, briefs, events, evidence, findings, overview, recommendations, runs, trends, watchlists
from .config import API_PREFIX

app = FastAPI(
    title="TideWatch API",
    description="Read-only query API for TideWatch intelligence outputs",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)

for r in (
    overview.router,
    trends.router,
    findings.router,
    recommendations.router,
    briefs.router,
    alerts.router,
    events.router,
    evidence.router,
    watchlists.router,
    runs.router,
):
    app.include_router(r, prefix=API_PREFIX)


@app.get("/health")
def health():
    return {"status": "ok"}
