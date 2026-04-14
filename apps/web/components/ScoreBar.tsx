"use client";

export default function ScoreBar({ value, label, max = 1 }: { value: number; label?: string; max?: number }) {
  const pct = Math.min(100, (value / max) * 100);
  const color = pct > 66 ? "var(--success)" : pct > 33 ? "var(--warning)" : "var(--text-muted)";
  return (
    <div>
      {label && <span style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>{label}</span>}
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <div className="score-bar" style={{ flex: 1 }}>
          <div className="score-bar-fill" style={{ width: `${pct}%`, background: color }} />
        </div>
        <span style={{ fontSize: "0.8rem", fontWeight: 600, minWidth: 36 }}>{value.toFixed(2)}</span>
      </div>
    </div>
  );
}
