"use client";

import Link from "next/link";
import { useApi } from "@/hooks/useApi";
import { getOverview } from "@/lib/api";
import MetricCard from "@/components/MetricCard";
import ScoreBar from "@/components/ScoreBar";
import Badge from "@/components/Badge";
import WhyItMattersPanel from "@/components/WhyItMattersPanel";

export default function DashboardPage() {
  const { data, loading, error } = useApi(() => getOverview(), []);

  if (loading) return <div className="loading">Loading dashboard...</div>;
  if (error) return <div className="error">Error: {error}</div>;
  if (!data) return null;

  const c = data.counts || {};
  const run = data.latest_run;

  return (
    <>
      <div className="page-header">
        <h1>Intelligence Dashboard</h1>
        {run && (
          <p>
            Run: <Link href={`/runs`}>{run.run_id}</Link>
            {" "}&middot;{" "}
            <Badge text={run.status || "unknown"} variant={run.status === "completed" ? "success" : "info"} />
            {run.started_at && <span> &middot; {new Date(run.started_at).toLocaleString()}</span>}
          </p>
        )}
      </div>

      <div className="grid-4 section">
        <MetricCard label="Documents" value={c.documents || 0} />
        <MetricCard label="Events" value={c.events || 0} />
        <MetricCard label="Trends" value={c.trends || 0} />
        <MetricCard label="Findings" value={c.findings || 0} />
        <MetricCard label="Evidence" value={c.evidence || 0} />
        <MetricCard label="Recommendations" value={c.recommendations || 0} color="var(--success)" />
        <MetricCard label="Briefs" value={c.briefs || 0} />
        <MetricCard label="Alerts" value={c.alerts || 0} color={c.alerts > 0 ? "var(--danger)" : undefined} />
      </div>

      {/* Top Trends */}
      {data.top_trends?.length > 0 && (
        <div className="section">
          <div className="section-title">Top Trends <Link href="/trends" className="btn" style={{ marginLeft: "auto" }}>View All</Link></div>
          <div className="table-wrap">
            <table>
              <thead><tr><th>Theme</th><th>Type</th><th>Strength</th><th>Novelty</th><th>Corroboration</th><th>Events</th></tr></thead>
              <tbody>
                {data.top_trends.map((t: any) => (
                  <tr key={t.trend_id}>
                    <td><Link href={`/trends?id=${t.trend_id}`}>{t.display_title || t.title || t.theme || t.subject || t.trend_id}</Link></td>
                    <td><Badge text={t.trend_type || "—"} /></td>
                    <td><ScoreBar value={t.strength_score} /></td>
                    <td><ScoreBar value={t.novelty_score} /></td>
                    <td><ScoreBar value={t.corroboration_score} /></td>
                    <td>{t.event_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Top Findings */}
      {data.top_findings?.length > 0 && (
        <div className="section">
          <div className="section-title">Top Findings <Link href="/findings" className="btn" style={{ marginLeft: "auto" }}>View All</Link></div>
          {data.top_findings.map((f: any) => (
            <div key={f.finding_id} className="card" style={{ marginBottom: 12 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                <div>
                  <Link href={`/findings/${f.finding_id}`} style={{ fontWeight: 600, fontSize: "1rem" }}>
                    {f.display_title || f.title || f.finding_id}
                  </Link>
                  <div style={{ display: "flex", gap: 8, marginTop: 4 }}>
                    <Badge text={f.finding_type || "finding"} />
                    {f.watchlist_hits?.length > 0 && <Badge text={`${f.watchlist_hits.length} watchlist hits`} variant="warning" />}
                  </div>
                </div>
                <div style={{ textAlign: "right" }}>
                  <ScoreBar value={f.importance_score} label="Importance" />
                  <ScoreBar value={f.decision_relevance_score} label="Decision Relevance" />
                </div>
              </div>
              <WhyItMattersPanel text={f.why_it_matters} />
            </div>
          ))}
        </div>
      )}

      {/* Top Recommendations */}
      {data.top_recommendations?.length > 0 && (
        <div className="section">
          <div className="section-title">Top Recommendations <Link href="/recommendations" className="btn" style={{ marginLeft: "auto" }}>View All</Link></div>
          <div className="table-wrap">
            <table>
              <thead><tr><th>Action</th><th>Priority</th><th>Rationale</th><th>Why Now</th></tr></thead>
              <tbody>
                {data.top_recommendations.map((r: any) => (
                  <tr key={r.recommendation_id}>
                    <td><Link href={`/recommendations?id=${r.recommendation_id}`}><Badge text={r.recommended_action || "—"} /></Link></td>
                    <td><ScoreBar value={r.priority} /></td>
                    <td style={{ maxWidth: 400, fontSize: "0.85rem" }}>{r.rationale}</td>
                    <td style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>{r.why_now}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Latest Briefs */}
      {data.latest_briefs?.length > 0 && (
        <div className="section">
          <div className="section-title">Latest Briefs <Link href="/briefs" className="btn" style={{ marginLeft: "auto" }}>View All</Link></div>
          {data.latest_briefs.map((b: any) => (
            <div key={b.brief_id} className="card" style={{ marginBottom: 12 }}>
              <Link href={`/briefs/${b.brief_id}`} style={{ fontWeight: 600 }}>{b.title || b.brief_id}</Link>
              <div style={{ display: "flex", gap: 16, marginTop: 8, fontSize: "0.85rem", color: "var(--text-muted)" }}>
                <span>{b.signal_count} signals</span>
                <span>{b.recommendation_count} recommendations</span>
                <Badge text={b.brief_type || "brief"} />
              </div>
              {b.summary && <p style={{ marginTop: 8, fontSize: "0.9rem" }}>{b.summary}</p>}
            </div>
          ))}
        </div>
      )}
    </>
  );
}
