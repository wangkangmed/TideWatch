"use client";

const VARIANT_MAP: Record<string, string> = {
  high: "badge-danger",
  critical: "badge-danger",
  medium: "badge-warning",
  low: "badge-info",
  info: "badge-info",
  success: "badge-success",
  watch: "badge-info",
  investigate: "badge-warning",
  act: "badge-danger",
};

export default function Badge({ text, variant }: { text: string; variant?: string }) {
  const cls = VARIANT_MAP[variant || text.toLowerCase()] || "badge-info";
  return <span className={`badge ${cls}`}>{text}</span>;
}
