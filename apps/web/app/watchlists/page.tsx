"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { useApi } from "@/hooks/useApi";
import { getWatchlist, getWatchlists } from "@/lib/api";
import Badge from "@/components/Badge";

function WatchlistsContent() {
  const params = useSearchParams();
  const detailId = params.get("id");
  const { data, loading, error } = useApi(() => getWatchlists({ page_size: 50 }), []);
  const { data: detail } = useApi(() => detailId ? getWatchlist(detailId) : Promise.resolve(null), [detailId]);

  if (loading) return <div className="loading">Loading watchlists...</div>;
  if (error) return <div className="error">Error: {error}</div>;

  const items = data?.items || [];

  return (
    <>
      <div className="page-header">
        <h1>Watchlists</h1>
        <p>Monitored entities and topics</p>
      </div>

      {detail && (
        <div className="card section">
          <h2 style={{ marginBottom: 16 }}>{detail.watchlist_id}</h2>

          {detail.entities?.length > 0 && (
            <div style={{ marginBottom: 20 }}>
              <div className="section-title">Entities ({detail.entities.length})</div>
              <div className="table-wrap">
                <table>
                  <thead><tr><th>Name</th><th>Type</th><th>Weight</th><th>Aliases</th></tr></thead>
                  <tbody>
                    {detail.entities.map((e: any, i: number) => (
                      <tr key={i}>
                        <td style={{ fontWeight: 500 }}>{e.canonical_name}</td>
                        <td><Badge text={e.entity_type || "—"} /></td>
                        <td>{e.weight?.toFixed(2)}</td>
                        <td><div className="chip-list">{e.aliases?.map((a: string, j: number) => <span key={j} className="chip">{a}</span>)}</div></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {detail.topics?.length > 0 && (
            <div>
              <div className="section-title">Topics ({detail.topics.length})</div>
              <div className="table-wrap">
                <table>
                  <thead><tr><th>Topic</th><th>Weight</th><th>Keywords</th></tr></thead>
                  <tbody>
                    {detail.topics.map((t: any, i: number) => (
                      <tr key={i}>
                        <td style={{ fontWeight: 500 }}>{t.topic_name}</td>
                        <td>{t.weight?.toFixed(2)}</td>
                        <td><div className="chip-list">{t.keywords?.map((k: string, j: number) => <span key={j} className="chip">{k}</span>)}</div></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      <div className="table-wrap">
        <table>
          <thead><tr><th>Watchlist</th><th>Entities</th><th>Topics</th></tr></thead>
          <tbody>
            {items.map((w: any) => (
              <tr key={w.watchlist_id} style={w.watchlist_id === detailId ? { background: "var(--bg-hover)" } : {}}>
                <td><Link href={`/watchlists?id=${w.watchlist_id}`}>{w.watchlist_id}</Link></td>
                <td>{w.entity_count}</td>
                <td>{w.topic_count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {items.length === 0 && <div className="loading">No watchlists available</div>}
    </>
  );
}

export default function WatchlistsPage() {
  return <Suspense fallback={<div className="loading">Loading...</div>}><WatchlistsContent /></Suspense>;
}
