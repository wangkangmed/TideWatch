"use client";

import Link from "next/link";
import { useApi } from "@/hooks/useApi";
import { getBrief } from "@/lib/api";
import Badge from "@/components/Badge";

export default function BriefDetailPage({ params }: { params: { id: string } }) {
  const { data, loading, error } = useApi(() => getBrief(params.id), [params.id]);

  if (loading) return <div className="loading">Loading brief...</div>;
  if (error) return <div className="error">Error: {error}</div>;
  if (!data) return <div className="error">Brief not found</div>;

  return (
    <>
      <div className="page-header">
        <p><Link href="/briefs">&larr; Back to Briefs</Link></p>
        <h1>{data.title || data.brief_id}</h1>
        <Badge text={data.brief_type || "brief"} />
      </div>

      {data.summary && <p style={{ fontSize: "1rem", marginBottom: 20 }}>{data.summary}</p>}

      {data.narrative && (
        <div className="card section" style={{ whiteSpace: "pre-line", lineHeight: 1.6 }}>
          {data.narrative}
        </div>
      )}

      <div className="grid-3 section">
        <div className="card" style={{ textAlign: "center" }}>
          <div className="metric-value">{data.key_signals?.length || 0}</div>
          <div className="metric-label">Key Signals</div>
        </div>
        <div className="card" style={{ textAlign: "center" }}>
          <div className="metric-value" style={{ color: "var(--success)" }}>{data.recommendations?.length || 0}</div>
          <div className="metric-label">Recommendations</div>
        </div>
        <div className="card" style={{ textAlign: "center" }}>
          <div className="metric-value">{data.supporting_finding_ids?.length || 0}</div>
          <div className="metric-label">Findings</div>
        </div>
      </div>

      {data.sections?.length > 0 && (
        <div className="section">
          <div className="section-title">Sections</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {data.sections.map((section: any, idx: number) => (
              <div key={idx} className="card">
                <div style={{ fontWeight: 600, marginBottom: 8 }}>{section.heading || `Section ${idx + 1}`}</div>
                {section.summary && (
                  <p style={{ marginBottom: 10, color: "var(--text-muted)", whiteSpace: "pre-line" }}>
                    {section.summary}
                  </p>
                )}
                {section.bullet_points?.length > 0 && (
                  <ul style={{ paddingLeft: 20, marginBottom: 10 }}>
                    {section.bullet_points.map((point: string, pointIdx: number) => (
                      <li key={pointIdx} style={{ marginBottom: 4 }}>{point}</li>
                    ))}
                  </ul>
                )}
                <div style={{ display: "flex", flexWrap: "wrap", gap: 8, fontSize: "0.8rem", color: "var(--text-muted)" }}>
                  {section.finding_ids?.length > 0 && <span>{section.finding_ids.length} findings</span>}
                  {section.recommendation_ids?.length > 0 && <span>{section.recommendation_ids.length} recommendations</span>}
                  {section.event_ids?.length > 0 && <span>{section.event_ids.length} events</span>}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {data.top_risks?.length > 0 && (
        <div className="section">
          <div className="section-title">Top Risks</div>
          <div className="chip-list">{data.top_risks.map((r: string, i: number) => <span key={i} className="chip" style={{ borderColor: "var(--danger)", color: "var(--danger)" }}>{r}</span>)}</div>
        </div>
      )}

      {data.top_opportunities?.length > 0 && (
        <div className="section">
          <div className="section-title">Top Opportunities</div>
          <div className="chip-list">{data.top_opportunities.map((o: string, i: number) => <span key={i} className="chip" style={{ borderColor: "var(--success)", color: "var(--success)" }}>{o}</span>)}</div>
        </div>
      )}

      {data.top_watch_items?.length > 0 && (
        <div className="section">
          <div className="section-title">Watch Items</div>
          <div className="chip-list">{data.top_watch_items.map((w: string, i: number) => <span key={i} className="chip">{w}</span>)}</div>
        </div>
      )}

      {data.continue_watching?.length > 0 && (
        <div className="section">
          <div className="section-title">Continue Watching</div>
          <ul style={{ paddingLeft: 20 }}>
            {data.continue_watching.map((item: string, idx: number) => (
              <li key={idx} style={{ marginBottom: 4 }}>{item}</li>
            ))}
          </ul>
        </div>
      )}

      {data.supporting_finding_ids?.length > 0 && (
        <div className="section">
          <div className="section-title">Supporting Findings</div>
          <div className="chip-list">
            {data.supporting_finding_ids.map((fid: string) => (
              <Link key={fid} href={`/findings/${fid}`} className="chip">{fid}</Link>
            ))}
          </div>
        </div>
      )}

      {data.supporting_event_ids?.length > 0 && (
        <div className="section">
          <div className="section-title">Supporting Events</div>
          <div className="chip-list">
            {data.supporting_event_ids.map((eid: string) => (
              <Link key={eid} href={`/events?id=${eid}`} className="chip">{eid}</Link>
            ))}
          </div>
        </div>
      )}

      {data.recommendation_objects?.length > 0 && (
        <div className="section">
          <div className="section-title">Consolidated Recommendations</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {data.recommendation_objects.map((rec: any, idx: number) => (
              <div key={idx} className="card">
                <div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
                  <div>
                    <Link href={`/recommendations?id=${rec.recommendation_id}`} style={{ fontWeight: 600 }}>
                      {rec.display_action || rec.recommended_action || rec.recommendation_id}
                    </Link>
                    {rec.rationale && <p style={{ marginTop: 6 }}>{rec.rationale}</p>}
                    {rec.why_now && (
                      <p style={{ marginTop: 4, fontSize: "0.85rem", color: "var(--text-muted)" }}>
                        Why now: {rec.why_now}
                      </p>
                    )}
                  </div>
                  <div style={{ minWidth: 120, textAlign: "right" }}>
                    <div style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>Priority</div>
                    <div style={{ fontWeight: 600 }}>{(rec.priority || 0).toFixed(2)}</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {data.recommendations?.length > 0 && (
        <div className="section">
          <div className="section-title">Recommendation IDs</div>
          <div className="chip-list">
            {data.recommendations.map((rid: string) => (
              <Link key={rid} href={`/recommendations?id=${rid}`} className="chip">{rid}</Link>
            ))}
          </div>
        </div>
      )}
    </>
  );
}
