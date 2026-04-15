"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { useApi } from "@/hooks/useApi";
import { getTrend, getTrends } from "@/lib/api";
import ScoreBar from "@/components/ScoreBar";
import Badge from "@/components/Badge";
import WhyItMattersPanel from "@/components/WhyItMattersPanel";

function TrendsContent() {
  const params = useSearchParams();
  const detailId = params.get("id");
  const { data, loading, error } = useApi(() => getTrends({ page_size: 50 }), []);
  const { data: detail } = useApi(() => detailId ? getTrend(detailId) : Promise.resolve(null), [detailId]);

  if (loading) return <div className="loading">Loading trends...</div>;
  if (error) return <div className="error">Error: {error}</div>;

  const items = data?.items || [];

  return (
    <>
      <div className="page-header">
        <h1>Trends</h1>
        <p>Detected patterns and signals across monitored sources</p>
      </div>

      {detail && (
        <div className="card section">
          <h2 style={{ marginBottom: 12 }}>{detail.display_title || detail.title || detail.theme || detail.subject || detail.trend_id}</h2>
          <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
            <Badge text={detail.trend_type || "trend"} />
            <Badge text={detail.direction || "—"} variant="info" />
            <Badge text={`${detail.event_count || 0} events`} variant="info" />
            <Badge text={`${detail.evidence_count || 0} evidence`} variant="info" />
          </div>
          {detail.summary && <p style={{ marginBottom: 12, color: "var(--text-muted)" }}>{detail.summary}</p>}
          <div className="grid-3" style={{ marginBottom: 16 }}>
            <ScoreBar value={detail.strength_score} label="Strength" />
            <ScoreBar value={detail.novelty_score} label="Novelty" />
            <ScoreBar value={detail.corroboration_score} label="Corroboration" />
          </div>
          <WhyItMattersPanel text={detail.why_it_matters} />
          {detail.explain?.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <div className="section-title">Explain</div>
              <ul style={{ paddingLeft: 20, marginTop: 8 }}>
                {detail.explain.map((line: string, idx: number) => <li key={idx} style={{ marginBottom: 4 }}>{line}</li>)}
              </ul>
            </div>
          )}
          {detail.related_events?.length > 0 ? (
            <div style={{ marginTop: 12 }}>
              <div className="section-title">Related Events</div>
              <div style={{ display: "flex", flexDirection: "column", gap: 8, marginTop: 8 }}>
                {detail.related_events.map((ev: any) => (
                  <div key={ev.event_id} className="card" style={{ padding: 12 }}>
                    <Link href={`/events?id=${ev.event_id}`} style={{ fontWeight: 600 }}>
                      {ev.canonical_title || ev.event_id}
                    </Link>
                    <div style={{ display: "flex", gap: 8, marginTop: 6 }}>
                      {ev.event_type && <Badge text={ev.event_type} />}
                      <span style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
                        Significance {Number(ev.significance_score || 0).toFixed(2)}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : detail.event_ids?.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <div className="section-title">Related Events</div>
              <div className="chip-list">
                {detail.event_ids.map((eid: string) => (
                  <Link key={eid} href={`/events?id=${eid}`} className="chip">{eid}</Link>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      <div className="table-wrap">
        <table>
          <thead>
            <tr><th>Trend</th><th>Subject</th><th>Type</th><th>Direction</th><th>Strength</th><th>Novelty</th><th>Corroboration</th><th>Confidence</th><th>Events</th></tr>
          </thead>
          <tbody>
            {items.map((t: any) => (
              <tr key={t.trend_id} style={t.trend_id === detailId ? { background: "var(--bg-hover)" } : {}}>
                <td>
                  <Link href={`/trends?id=${t.trend_id}`}>{t.display_title || t.title || t.theme || t.subject || t.trend_id}</Link>
                  {t.summary && <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginTop: 4 }}>{t.summary}</div>}
                </td>
                <td>{t.subject || "—"}</td>
                <td><Badge text={t.trend_type || "—"} /></td>
                <td>{t.direction || "—"}</td>
                <td><ScoreBar value={t.strength_score} /></td>
                <td><ScoreBar value={t.novelty_score} /></td>
                <td><ScoreBar value={t.corroboration_score} /></td>
                <td>{t.confidence?.toFixed(2)}</td>
                <td>{t.event_count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

export default function TrendsPage() {
  return <Suspense fallback={<div className="loading">Loading...</div>}><TrendsContent /></Suspense>;
}
