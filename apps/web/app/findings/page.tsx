"use client";

import Link from "next/link";
import { useApi } from "@/hooks/useApi";
import { getFindings } from "@/lib/api";
import ScoreBar from "@/components/ScoreBar";
import Badge from "@/components/Badge";
import WhyItMattersPanel from "@/components/WhyItMattersPanel";

export default function FindingsPage() {
  const { data, loading, error } = useApi(() => getFindings({ page_size: 50 }), []);

  if (loading) return <div className="loading">Loading findings...</div>;
  if (error) return <div className="error">Error: {error}</div>;

  const items = data?.items || [];

  return (
    <>
      <div className="page-header">
        <h1>Findings</h1>
        <p>Intelligence findings with importance and decision relevance scoring</p>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        {items.map((f: any) => (
          <div key={f.finding_id} className="card">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
              <div>
                <Link href={`/findings/${f.finding_id}`} style={{ fontWeight: 600, fontSize: "1.05rem" }}>
                  {f.title || f.finding_id}
                </Link>
                <div style={{ display: "flex", gap: 6, marginTop: 6 }}>
                  <Badge text={f.finding_type || "finding"} />
                  {f.theme && <Badge text={f.theme} variant="info" />}
                  {f.watchlist_hits?.length > 0 && <Badge text={`${f.watchlist_hits.length} WL hits`} variant="warning" />}
                </div>
              </div>
              <div style={{ textAlign: "right", minWidth: 180 }}>
                <ScoreBar value={f.importance_score} label="Importance" />
                <ScoreBar value={f.decision_relevance_score} label="Decision Rel." />
                <ScoreBar value={f.confidence} label="Confidence" />
              </div>
            </div>
            {f.summary && <p style={{ marginTop: 10, fontSize: "0.9rem", color: "var(--text-muted)" }}>{f.summary}</p>}
            <WhyItMattersPanel text={f.why_it_matters} />
            <div style={{ display: "flex", gap: 16, marginTop: 8, fontSize: "0.8rem", color: "var(--text-muted)" }}>
              <span>{f.event_count} events</span>
              <span>{f.evidence_count} evidence items</span>
            </div>
            {f.recommended_actions?.length > 0 && (
              <div style={{ marginTop: 10 }}>
                <div style={{ fontSize: "0.8rem", fontWeight: 600, color: "var(--text-muted)", marginBottom: 4 }}>Recommended Actions</div>
                <ul style={{ paddingLeft: 20, fontSize: "0.85rem" }}>
                  {f.recommended_actions.map((a: string, i: number) => <li key={i}>{a}</li>)}
                </ul>
              </div>
            )}
          </div>
        ))}
      </div>
    </>
  );
}
