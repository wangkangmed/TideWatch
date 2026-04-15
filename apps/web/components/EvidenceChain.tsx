"use client";

import Link from "next/link";

interface EvidenceItem {
  evidence_id?: string;
  item_id?: string;
  document?: { title?: string; canonical_url?: string; source_id?: string };
  title?: string;
  canonical_url?: string;
  source_id?: string;
}

export default function EvidenceChain({ items }: { items: EvidenceItem[] }) {
  if (!items || items.length === 0) return <span style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>No evidence linked</span>;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      {items.map((ev, i) => {
        const id = ev.evidence_id || ev.item_id || `evi-${i}`;
        const doc = ev.document || {};
        const title = doc.title || ev.title || id;
        const url = doc.canonical_url || ev.canonical_url;
        const source = doc.source_id || ev.source_id;
        return (
          <div key={i} className="card" style={{ padding: 12 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <div style={{ fontSize: "0.9rem", fontWeight: 500 }}>{title}</div>
                {source && <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>{source}</span>}
              </div>
              {url && (
                <a href={url} target="_blank" rel="noopener noreferrer" className="btn" style={{ fontSize: "0.75rem" }}>
                  Source
                </a>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
