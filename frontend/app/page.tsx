import Link from "next/link";

export default function Home() {
  return (
    <main className="container" style={{ paddingTop: 72, paddingBottom: 72 }}>
      <section className="card" style={{ padding: 48 }}>
        <div style={{ maxWidth: 720 }}>
          <p style={{ margin: 0, color: "#60a5fa", fontWeight: 700, letterSpacing: "0.15em" }}>
            AstroCycle
          </p>
          <h1 style={{ margin: "1rem 0", fontSize: "3rem", lineHeight: 1.05 }}>
            Cycle forecasting platform for modern retail traders.
          </h1>
          <p style={{ margin: "1.5rem 0", color: "#cbd5e1", fontSize: "1.05rem", lineHeight: 1.8 }}>
            Build a SaaS-ready astro cycle dashboard with subscription-based authentication,
            market cycle scanners, and realtime composite visualization.
          </p>
          <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
            <Link href="/login" className="button">
              Get Started
            </Link>
            <Link href="/dashboard" className="button" style={{ background: "rgba(148, 163, 184, 0.16)" }}>
              View Dashboard
            </Link>
          </div>
        </div>
      </section>
    </main>
  );
}
