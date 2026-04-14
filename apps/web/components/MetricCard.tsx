"use client";

export default function MetricCard({ label, value, color }: { label: string; value: number | string; color?: string }) {
  return (
    <div className="card" style={{ textAlign: "center" }}>
      <div className="metric-value" style={color ? { color } : {}}>{value}</div>
      <div className="metric-label">{label}</div>
    </div>
  );
}
