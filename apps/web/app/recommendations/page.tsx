"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { useApi } from "@/hooks/useApi";
import { getRecommendation, getRecommendations } from "@/lib/api";
import ScoreBar from "@/components/ScoreBar";
import Badge from "@/components/Badge";

function RecommendationsContent() {
  const params = useSearchParams();
  const detailId = params.get("id");
  const { data, loading, error } = useApi(() => getRecommendations({ page_size: 50 }), []);
  const { data: detail } = useApi(() => detailId ? getRecommendation(detailId) : Promise.resolve(null), [detailId]);

  if (loading) return <div className="loading">Loading recommendations...</div>;
  if (error) return <div className="error">Error: {error}</div>;

  const items = data?.items || [];

  return (
    <>
      <div className="page-header">
        <h1>Recommendations</h1>
        <p>Actionable recommendations from decision support analysis</p>
      </div>

      {detail && (
        <div className="card section">
          <h2 style={{ marginBottom: 8 }}>
            <Badge text={detail.display_action || detail.recommended_action || "—"} />
          </h2>
          <ScoreBar value={detail.priority} label="Priority" />
          {detail.rationale && <p style={{ marginTop: 12 }}>{detail.rationale}</p>}
          {detail.why_now && (
            <div className="why-panel" style={{ marginTop: 12 }}>
              <strong>Why Now:</strong> {detail.why_now}
            </div>
          )}
          {detail.priority_explain?.length > 0 && (
            <div style={{ marginTop: 12, fontSize: "0.85rem", color: "var(--text-muted)" }}>
              <strong>Priority Explain:</strong>
              <ul style={{ marginTop: 6, paddingLeft: 20 }}>
                {detail.priority_explain.map((item: string, idx: number) => <li key={idx}>{item}</li>)}
              </ul>
            </div>
          )}
          <div style={{ display: "flex", gap: 16, marginTop: 12, fontSize: "0.8rem", color: "var(--text-muted)" }}>
            <span>{detail.finding_count} findings</span>
            <span>{detail.event_count} events</span>
            <span>{detail.evidence_count} evidence</span>
          </div>
          {detail.action_group && (
            <div style={{ marginTop: 10, fontSize: "0.8rem", color: "var(--text-muted)" }}>
              Group: {detail.action_group.replaceAll("_", " ")}
            </div>
          )}
          {detail.related_signal && (
            <div style={{ marginTop: 16 }}>
              <div className="section-title">Source Signal</div>
              <div className="card" style={{ padding: 12 }}>
                <Badge text={detail.related_signal.signal_type || "signal"} />
                <span style={{ marginLeft: 8 }}>{detail.related_signal.why_it_matters?.slice(0, 200)}</span>
              </div>
            </div>
          )}
          {detail.related_findings?.length > 0 && (
            <div style={{ marginTop: 16 }}>
              <div className="section-title">Supporting Findings</div>
              {detail.related_findings.map((f: any, i: number) => (
                <div key={i} className="card" style={{ marginBottom: 8, padding: 12 }}>
                  <Link href={`/findings/${f.finding_id}`}>{f.title || f.finding_id}</Link>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {items.map((r: any) => (
          <div key={r.recommendation_id} className="card" style={r.recommendation_id === detailId ? { borderColor: "var(--accent)" } : {}}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
              <div>
                <Link href={`/recommendations?id=${r.recommendation_id}`}>
                  <Badge text={r.display_action || r.recommended_action || "—"} />
                </Link>
                {r.rationale && <p style={{ marginTop: 6, fontSize: "0.9rem" }}>{r.rationale}</p>}
                {r.why_now && <p style={{ marginTop: 4, fontSize: "0.8rem", color: "var(--text-muted)" }}>Why now: {r.why_now}</p>}
                {r.action_group && (
                  <p style={{ marginTop: 4, fontSize: "0.75rem", color: "var(--text-muted)" }}>
                    Group: {r.action_group.replaceAll("_", " ")}
                  </p>
                )}
              </div>
              <div style={{ textAlign: "right", minWidth: 140 }}>
                <ScoreBar value={r.priority} label="Priority" />
                <div style={{ marginTop: 8, fontSize: "0.75rem", color: "var(--text-muted)" }}>
                  {r.finding_count}F / {r.event_count}E / {r.evidence_count}Ev
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </>
  );
}

export default function RecommendationsPage() {
  return <Suspense fallback={<div className="loading">Loading...</div>}><RecommendationsContent /></Suspense>;
}
