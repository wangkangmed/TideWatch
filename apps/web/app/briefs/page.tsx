"use client";

import Link from "next/link";
import { useApi } from "@/hooks/useApi";
import { getBriefs } from "@/lib/api";
import Badge from "@/components/Badge";

export default function BriefsPage() {
  const { data, loading, error } = useApi(() => getBriefs({ page_size: 50 }), []);

  if (loading) return <div className="loading">Loading briefs...</div>;
  if (error) return <div className="error">Error: {error}</div>;

  const items = data?.items || [];

  return (
    <>
      <div className="page-header">
        <h1>Decision Briefs</h1>
        <p>Synthesized intelligence briefs for decision makers</p>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        {items.map((b: any) => (
          <div key={b.brief_id} className="card">
            <Link href={`/briefs/${b.brief_id}`} style={{ fontWeight: 600, fontSize: "1.05rem" }}>
              {b.title || b.brief_id}
            </Link>
            <div style={{ display: "flex", gap: 12, marginTop: 8 }}>
              <Badge text={b.brief_type || "brief"} />
              <span style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>{b.signal_count} signals</span>
              <span style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>{b.recommendation_count} recommendations</span>
            </div>
            {b.summary && <p style={{ marginTop: 10, fontSize: "0.9rem" }}>{b.summary}</p>}
          </div>
        ))}
        {items.length === 0 && <div className="loading">No briefs available</div>}
      </div>
    </>
  );
}
