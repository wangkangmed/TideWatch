"use client";

import Link from "next/link";
import { useApi } from "@/hooks/useApi";
import { getFinding } from "@/lib/api";
import ScoreBar from "@/components/ScoreBar";
import Badge from "@/components/Badge";
import WhyItMattersPanel from "@/components/WhyItMattersPanel";
import EvidenceChain from "@/components/EvidenceChain";

export default function FindingDetailPage({ params }: { params: { id: string } }) {
  const { data, loading, error } = useApi(() => getFinding(params.id), [params.id]);

  if (loading) return <div className="loading">Loading finding...</div>;
  if (error) return <div className="error">Error: {error}</div>;
  if (!data) return <div className="error">Finding not found</div>;

  return (
    <>
      <div className="page-header">
        <p><Link href="/findings">&larr; Back to Findings</Link></p>
        <h1>{data.title || data.finding_id}</h1>
        <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
          <Badge text={data.finding_type || "finding"} />
          {data.theme && <Badge text={data.theme} variant="info" />}
          {data.watchlist_hits?.length > 0 && <Badge text={`${data.watchlist_hits.length} watchlist hits`} variant="warning" />}
        </div>
      </div>

      <div className="grid-3 section">
        <div className="card">
          <ScoreBar value={data.importance_score} label="Importance Score" />
        </div>
        <div className="card">
          <ScoreBar value={data.decision_relevance_score} label="Decision Relevance" />
        </div>
        <div className="card">
          <ScoreBar value={data.confidence} label="Confidence" />
        </div>
      </div>

      {data.summary && <p style={{ fontSize: "1rem", marginBottom: 16 }}>{data.summary}</p>}
      <WhyItMattersPanel text={data.why_it_matters} />

      {data.recommended_actions?.length > 0 && (
        <div className="section">
          <div className="section-title">Recommended Actions</div>
          <ul style={{ paddingLeft: 24 }}>
            {data.recommended_actions.map((a: string, i: number) => <li key={i} style={{ marginBottom: 4 }}>{a}</li>)}
          </ul>
        </div>
      )}

      {data.related_trend && (
        <div className="section">
          <div className="section-title">Related Trend</div>
          <div className="card">
            <Link href={`/trends?id=${data.related_trend.trend_id}`} style={{ fontWeight: 600 }}>
              {data.related_trend.theme || data.related_trend.trend_id}
            </Link>
            <div className="grid-3" style={{ marginTop: 12 }}>
              <ScoreBar value={data.related_trend.strength_score || 0} label="Strength" />
              <ScoreBar value={data.related_trend.novelty_score || 0} label="Novelty" />
              <ScoreBar value={data.related_trend.corroboration_score || 0} label="Corroboration" />
            </div>
          </div>
        </div>
      )}

      {data.related_events?.length > 0 && (
        <div className="section">
          <div className="section-title">Related Events ({data.related_events.length})</div>
          {data.related_events.map((ev: any, i: number) => (
            <div key={i} className="card" style={{ marginBottom: 8 }}>
              <Link href={`/events?id=${ev.event_id}`} style={{ fontWeight: 500 }}>
                {ev.canonical_title || ev.event_id}
              </Link>
              <div style={{ display: "flex", gap: 8, marginTop: 4 }}>
                {ev.event_type && <Badge text={ev.event_type} />}
                {ev.significance_score && <span style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>Significance: {ev.significance_score.toFixed(2)}</span>}
              </div>
            </div>
          ))}
        </div>
      )}

      {data.related_evidence?.length > 0 && (
        <div className="section">
          <div className="section-title">Supporting Evidence ({data.related_evidence.length})</div>
          <EvidenceChain items={data.related_evidence} />
        </div>
      )}

      {data.related_recommendations?.length > 0 && (
        <div className="section">
          <div className="section-title">Related Recommendations</div>
          {data.related_recommendations.map((r: any, i: number) => (
            <div key={i} className="card" style={{ marginBottom: 8 }}>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <div>
                  <Badge text={r.recommended_action || "—"} />
                  {r.rationale && <p style={{ fontSize: "0.85rem", marginTop: 6 }}>{r.rationale}</p>}
                </div>
                <ScoreBar value={r.priority || 0} label="Priority" />
              </div>
            </div>
          ))}
        </div>
      )}

      {data.metadata && Object.keys(data.metadata).length > 0 && (
        <div className="section">
          <div className="section-title">Metadata</div>
          <pre className="card" style={{ fontSize: "0.8rem", overflow: "auto", maxHeight: 300 }}>
            {JSON.stringify(data.metadata, null, 2)}
          </pre>
        </div>
      )}
    </>
  );
}
