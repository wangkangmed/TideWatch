"use client";

export default function WhyItMattersPanel({ text }: { text: string | null | undefined }) {
  if (!text) return null;
  return (
    <div className="why-panel">
      <div style={{ fontSize: "0.8rem", fontWeight: 600, color: "var(--accent)", marginBottom: 6, textTransform: "uppercase", letterSpacing: "0.04em" }}>
        Why It Matters
      </div>
      {text}
    </div>
  );
}
