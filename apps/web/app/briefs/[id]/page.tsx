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

      {data.recommendations?.length > 0 && (
        <div className="section">
          <div className="section-title">Recommendations</div>
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
