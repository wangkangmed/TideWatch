"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { useApi } from "@/hooks/useApi";
import { getEvent, getEvents } from "@/lib/api";
import ScoreBar from "@/components/ScoreBar";
import Badge from "@/components/Badge";
import EvidenceChain from "@/components/EvidenceChain";

function EventsContent() {
  const params = useSearchParams();
  const detailId = params.get("id");
  const { data, loading, error } = useApi(() => getEvents({ page_size: 50 }), []);
  const { data: detail } = useApi(() => detailId ? getEvent(detailId) : Promise.resolve(null), [detailId]);

  if (loading) return <div className="loading">Loading events...</div>;
  if (error) return <div className="error">Error: {error}</div>;

  const items = data?.items || [];

  return (
    <>
      <div className="page-header">
        <h1>Events</h1>
        <p>Detected events with evidence links and significance scores</p>
      </div>

      {detail && (
        <div className="card section">
          <h2 style={{ marginBottom: 8 }}>{detail.canonical_title || detail.event_id}</h2>
          <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
            {detail.event_type && <Badge text={detail.event_type} />}
            {detail.status && <Badge text={detail.status} variant="info" />}
          </div>
          <div className="grid-2" style={{ marginBottom: 16 }}>
            <ScoreBar value={detail.significance_score || 0} label="Significance" />
            <ScoreBar value={detail.confidence || 0} label="Confidence" />
          </div>
          <div className="detail-grid">
            <span className="detail-label">Subject</span><span className="detail-value">{detail.subject || "—"}</span>
            <span className="detail-label">Event Time</span><span className="detail-value">{detail.event_time || "—"}</span>
            <span className="detail-label">Precision</span><span className="detail-value">{detail.time_precision || "—"}</span>
          </div>
          {detail.evidence_items?.length > 0 && (
            <div style={{ marginTop: 16 }}>
              <div className="section-title">Evidence Chain ({detail.evidence_items.length})</div>
              <EvidenceChain items={detail.evidence_items} />
            </div>
          )}
        </div>
      )}

      <div className="table-wrap">
        <table>
          <thead>
            <tr><th>Title</th><th>Type</th><th>Subject</th><th>Significance</th><th>Confidence</th><th>Evidence</th></tr>
          </thead>
          <tbody>
            {items.map((ev: any) => (
              <tr key={ev.event_id} style={ev.event_id === detailId ? { background: "var(--bg-hover)" } : {}}>
                <td><Link href={`/events?id=${ev.event_id}`}>{ev.canonical_title || ev.event_id}</Link></td>
                <td>{ev.event_type && <Badge text={ev.event_type} />}</td>
                <td>{ev.subject || "—"}</td>
                <td><ScoreBar value={ev.significance_score || 0} /></td>
                <td>{ev.confidence?.toFixed(2)}</td>
                <td>{ev.evidence_count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

export default function EventsPage() {
  return <Suspense fallback={<div className="loading">Loading...</div>}><EventsContent /></Suspense>;
}
