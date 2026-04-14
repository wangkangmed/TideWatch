import "./globals.css";
import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "TideWatch – Intelligence Workspace",
  description: "Analyst dashboard for intelligence monitoring and decision support",
};

const NAV_ITEMS = [
  { href: "/", label: "Dashboard" },
  { href: "/trends", label: "Trends" },
  { href: "/findings", label: "Findings" },
  { href: "/recommendations", label: "Recommendations" },
  { href: "/briefs", label: "Briefs" },
  { href: "/events", label: "Events" },
  { href: "/watchlists", label: "Watchlists" },
  { href: "/runs", label: "Runs" },
];

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <nav style={{
          background: "var(--bg-card)",
          borderBottom: "1px solid var(--border)",
          padding: "0 24px",
          display: "flex",
          alignItems: "center",
          height: 56,
          gap: 24,
          position: "sticky",
          top: 0,
          zIndex: 100,
        }}>
          <Link href="/" style={{ fontWeight: 700, fontSize: "1.1rem", color: "var(--accent)", marginRight: 16 }}>
            TideWatch
          </Link>
          {NAV_ITEMS.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              style={{ color: "var(--text-muted)", fontSize: "0.9rem", fontWeight: 500 }}
            >
              {item.label}
            </Link>
          ))}
        </nav>
        <main className="container" style={{ paddingTop: 8, paddingBottom: 60 }}>
          {children}
        </main>
      </body>
    </html>
  );
}
