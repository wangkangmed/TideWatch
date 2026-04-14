"""Full five-layer pipeline persistence.

Writes all graph outputs (documents, evidence, events, intelligence,
decision support) to a SQLite database keyed by run_id.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

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

_SCHEMA = """
CREATE TABLE IF NOT EXISTS pipeline_runs (
  run_id TEXT PRIMARY KEY,
  status TEXT NOT NULL DEFAULT 'running',
  started_at TEXT NOT NULL,
  finished_at TEXT,
  metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS documents (
  run_id TEXT NOT NULL,
  document_id TEXT NOT NULL,
  title TEXT,
  canonical_url TEXT,
  published_at TEXT,
  content_hash TEXT,
  body_preview TEXT,
  doc_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  PRIMARY KEY (run_id, document_id)
);

CREATE TABLE IF NOT EXISTS evidence_items (
  run_id TEXT NOT NULL,
  evidence_id TEXT NOT NULL,
  document_id TEXT NOT NULL,
  source_id TEXT,
  item_json TEXT NOT NULL,
  source_trace_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL,
  PRIMARY KEY (run_id, evidence_id)
);

CREATE TABLE IF NOT EXISTS events (
  run_id TEXT NOT NULL,
  event_id TEXT NOT NULL,
  title TEXT,
  source_id TEXT,
  event_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  PRIMARY KEY (run_id, event_id)
);

CREATE TABLE IF NOT EXISTS event_evidence_links (
  run_id TEXT NOT NULL,
  link_id TEXT NOT NULL,
  event_id TEXT NOT NULL,
  evidence_id TEXT NOT NULL,
  link_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  PRIMARY KEY (run_id, link_id)
);

CREATE TABLE IF NOT EXISTS trend_signals (
  run_id TEXT NOT NULL,
  trend_id TEXT NOT NULL,
  title TEXT,
  trend_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  PRIMARY KEY (run_id, trend_id)
);

CREATE TABLE IF NOT EXISTS intelligence_findings (
  run_id TEXT NOT NULL,
  finding_id TEXT NOT NULL,
  finding_type TEXT,
  finding_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  PRIMARY KEY (run_id, finding_id)
);

CREATE TABLE IF NOT EXISTS alert_items (
  run_id TEXT NOT NULL,
  alert_id TEXT NOT NULL,
  alert_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  PRIMARY KEY (run_id, alert_id)
);

CREATE TABLE IF NOT EXISTS briefing_items (
  run_id TEXT NOT NULL,
  briefing_item_id TEXT NOT NULL,
  briefing_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  PRIMARY KEY (run_id, briefing_item_id)
);

CREATE TABLE IF NOT EXISTS decision_signals (
  run_id TEXT NOT NULL,
  signal_id TEXT NOT NULL,
  finding_id TEXT,
  signal_type TEXT,
  signal_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  PRIMARY KEY (run_id, signal_id)
);

CREATE TABLE IF NOT EXISTS recommendation_items (
  run_id TEXT NOT NULL,
  recommendation_id TEXT NOT NULL,
  signal_id TEXT,
  recommended_action TEXT,
  rec_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  PRIMARY KEY (run_id, recommendation_id)
);

CREATE TABLE IF NOT EXISTS decision_briefs (
  run_id TEXT NOT NULL,
  brief_id TEXT NOT NULL,
  brief_type TEXT,
  brief_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  PRIMARY KEY (run_id, brief_id)
);

CREATE INDEX IF NOT EXISTS idx_docs_run ON documents(run_id);
CREATE INDEX IF NOT EXISTS idx_evi_run ON evidence_items(run_id);
CREATE INDEX IF NOT EXISTS idx_evt_run ON events(run_id);
CREATE INDEX IF NOT EXISTS idx_eel_evt ON event_evidence_links(run_id, event_id);
CREATE INDEX IF NOT EXISTS idx_trends_run ON trend_signals(run_id);
CREATE INDEX IF NOT EXISTS idx_findings_run ON intelligence_findings(run_id);
CREATE INDEX IF NOT EXISTS idx_ds_finding ON decision_signals(run_id, finding_id);
CREATE INDEX IF NOT EXISTS idx_rec_signal ON recommendation_items(run_id, signal_id);
"""


def _model_json(obj: Any) -> str:
    if hasattr(obj, "model_dump"):
        return json.dumps(obj.model_dump(mode="json"), ensure_ascii=False)
    if isinstance(obj, dict):
        return json.dumps(obj, ensure_ascii=False, default=str)
    return json.dumps(obj, ensure_ascii=False, default=str)


class PipelineRepository:
    def __init__(self, db_path: str | None = None) -> None:
        base = Path(db_path) if db_path else Path(__file__).resolve().parents[3] / "data" / "pipeline_runs.sqlite3"
        if str(base) != ":memory:":
            base.parent.mkdir(parents=True, exist_ok=True)
        self.db_path = str(base)
        self._init()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _init(self) -> None:
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    # -- pipeline run lifecycle --

    def start_run(self, run_id: str, metadata: dict[str, Any] | None = None) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO pipeline_runs (run_id, status, started_at, metadata_json) VALUES (?, ?, ?, ?)",
                (run_id, "running", self._now(), json.dumps(metadata or {}, ensure_ascii=False)),
            )

    def finish_run(self, run_id: str, status: str = "completed") -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE pipeline_runs SET status = ?, finished_at = ? WHERE run_id = ?",
                (status, self._now(), run_id),
            )

    # -- Layer 2: documents + evidence --

    def save_documents(self, run_id: str, docs: list[NormalizedDocument]) -> None:
        now = self._now()
        with self._connect() as conn:
            for doc in docs:
                conn.execute(
                    "INSERT OR REPLACE INTO documents "
                    "(run_id, document_id, title, canonical_url, published_at, content_hash, body_preview, doc_json, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        run_id, doc.doc_id, doc.title, doc.canonical_url,
                        str(doc.published_at) if doc.published_at else None,
                        doc.fingerprint, (doc.body_text or "")[:500],
                        _model_json(doc), now,
                    ),
                )

    def save_evidence(self, run_id: str, items: list[EvidenceItem | dict]) -> None:
        now = self._now()
        with self._connect() as conn:
            for item in items:
                if isinstance(item, dict):
                    evi_id = item.get("evidence_id", "")
                    doc_id = item.get("doc_id", "")
                    src_id = item.get("source_id", "")
                    trace = item.get("source_trace", {})
                else:
                    evi_id = item.evidence_id
                    doc_id = item.doc_id
                    src_id = item.source_id
                    trace = item.source_trace
                conn.execute(
                    "INSERT OR REPLACE INTO evidence_items "
                    "(run_id, evidence_id, document_id, source_id, item_json, source_trace_json, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (run_id, evi_id, doc_id, src_id, _model_json(item), json.dumps(trace, ensure_ascii=False, default=str), now),
                )

    # -- Layer 3: events --

    def save_events(self, run_id: str, events: list[EventItem | dict], links: list[EventEvidenceLink | dict]) -> None:
        now = self._now()
        with self._connect() as conn:
            for evt in events:
                if isinstance(evt, dict):
                    eid, title, sid = evt.get("event_id", ""), evt.get("title", ""), evt.get("source_id")
                else:
                    eid, title, sid = evt.event_id, evt.title, evt.source_id
                conn.execute(
                    "INSERT OR REPLACE INTO events (run_id, event_id, title, source_id, event_json, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (run_id, eid, title, sid, _model_json(evt), now),
                )
            for link in links:
                if isinstance(link, dict):
                    lid, evid, eviid = link.get("link_id", ""), link.get("event_id", ""), link.get("evidence_id", "")
                else:
                    lid, evid, eviid = link.link_id, link.event_id, link.evidence_id
                conn.execute(
                    "INSERT OR REPLACE INTO event_evidence_links (run_id, link_id, event_id, evidence_id, link_json, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (run_id, lid, evid, eviid, _model_json(link), now),
                )

    # -- Layer 4: intelligence --

    def save_intelligence(
        self,
        run_id: str,
        trends: list[TrendSignal | dict],
        findings: list[Finding | dict],
        alerts: list[AlertItem | dict],
        briefings: list[BriefingItem | dict],
    ) -> None:
        now = self._now()
        with self._connect() as conn:
            for t in trends:
                tid = t.trend_id if isinstance(t, TrendSignal) else t.get("trend_id", "")
                title = t.title if isinstance(t, TrendSignal) else t.get("title")
                conn.execute(
                    "INSERT OR REPLACE INTO trend_signals (run_id, trend_id, title, trend_json, created_at) VALUES (?, ?, ?, ?, ?)",
                    (run_id, tid, title, _model_json(t), now),
                )
            for f in findings:
                fid = f.finding_id if isinstance(f, Finding) else f.get("finding_id", "")
                ftype = f.finding_type if isinstance(f, Finding) else f.get("finding_type")
                conn.execute(
                    "INSERT OR REPLACE INTO intelligence_findings (run_id, finding_id, finding_type, finding_json, created_at) VALUES (?, ?, ?, ?, ?)",
                    (run_id, fid, ftype, _model_json(f), now),
                )
            for a in alerts:
                aid = a.alert_id if isinstance(a, AlertItem) else a.get("alert_id", "")
                conn.execute(
                    "INSERT OR REPLACE INTO alert_items (run_id, alert_id, alert_json, created_at) VALUES (?, ?, ?, ?)",
                    (run_id, aid, _model_json(a), now),
                )
            for b in briefings:
                bid = b.briefing_id if isinstance(b, BriefingItem) else b.get("briefing_item_id", b.get("briefing_id", ""))
                conn.execute(
                    "INSERT OR REPLACE INTO briefing_items (run_id, briefing_item_id, briefing_json, created_at) VALUES (?, ?, ?, ?)",
                    (run_id, bid, _model_json(b), now),
                )

    # -- Layer 5: decision support --

    def save_decision_support(
        self,
        run_id: str,
        signals: list[DecisionSignal | dict],
        recommendations: list[RecommendationItem | dict],
        briefs: list[DecisionBrief | dict],
    ) -> None:
        now = self._now()
        with self._connect() as conn:
            for s in signals:
                sid = s.signal_id if isinstance(s, DecisionSignal) else s.get("signal_id", "")
                fid = s.finding_id if isinstance(s, DecisionSignal) else s.get("finding_id")
                stype = s.signal_type if isinstance(s, DecisionSignal) else s.get("signal_type")
                conn.execute(
                    "INSERT OR REPLACE INTO decision_signals (run_id, signal_id, finding_id, signal_type, signal_json, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (run_id, sid, fid, stype, _model_json(s), now),
                )
            for r in recommendations:
                rid = r.recommendation_id if isinstance(r, RecommendationItem) else r.get("recommendation_id", "")
                rsid = r.signal_id if isinstance(r, RecommendationItem) else r.get("signal_id")
                ract = r.recommended_action if isinstance(r, RecommendationItem) else r.get("recommended_action")
                conn.execute(
                    "INSERT OR REPLACE INTO recommendation_items (run_id, recommendation_id, signal_id, recommended_action, rec_json, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (run_id, rid, rsid, ract, _model_json(r), now),
                )
            for b in briefs:
                bid = b.brief_id if isinstance(b, DecisionBrief) else b.get("brief_id", "")
                btype = b.brief_type if isinstance(b, DecisionBrief) else b.get("brief_type")
                conn.execute(
                    "INSERT OR REPLACE INTO decision_briefs (run_id, brief_id, brief_type, brief_json, created_at) VALUES (?, ?, ?, ?, ?)",
                    (run_id, bid, btype, _model_json(b), now),
                )
