"use client";

import { useApi } from "@/hooks/useApi";
import { getRuns } from "@/lib/api";
import Badge from "@/components/Badge";

export default function RunsPage() {
  const { data, loading, error } = useApi(() => getRuns({ page_size: 50 }), []);

  if (loading) return <div className="loading">Loading runs...</div>;
  if (error) return <div className="error">Error: {error}</div>;

  const items = data?.items || [];

  return (
    <>
      <div className="page-header">
        <h1>Pipeline Runs</h1>
        <p>History of pipeline execution runs</p>
      </div>

      <div className="table-wrap">
        <table>
          <thead>
            <tr><th>Run ID</th><th>Status</th><th>Started</th><th>Finished</th><th>Docs</th><th>Events</th><th>Trends</th><th>Findings</th><th>Recs</th><th>Briefs</th></tr>
          </thead>
          <tbody>
            {items.map((r: any) => (
              <tr key={r.run_id}>
                <td style={{ fontWeight: 500, fontFamily: "monospace", fontSize: "0.85rem" }}>{r.run_id}</td>
                <td><Badge text={r.status || "—"} variant={r.status === "completed" ? "success" : "info"} /></td>
                <td style={{ fontSize: "0.85rem" }}>{r.started_at ? new Date(r.started_at).toLocaleString() : "—"}</td>
                <td style={{ fontSize: "0.85rem" }}>{r.finished_at ? new Date(r.finished_at).toLocaleString() : "—"}</td>
                <td>{r.document_count}</td>
                <td>{r.event_count}</td>
                <td>{r.trend_count}</td>
                <td>{r.finding_count}</td>
                <td>{r.recommendation_count}</td>
                <td>{r.brief_count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {items.length === 0 && <div className="loading">No runs available</div>}
    </>
  );
}
