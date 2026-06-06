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
            Platform prediksi siklus untuk trader ritel modern.
          </h1>
          <p style={{ margin: "1.5rem 0", color: "#cbd5e1", fontSize: "1.05rem", lineHeight: 1.8 }}>
            Pantau siklus pasar berbasis astro dengan scanner, titik balik, visualisasi komposit,
            dan ringkasan analisis yang siap dipakai untuk membaca momentum.
          </p>
          <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
            <Link href="/login" className="button">
              Mulai
            </Link>
            <Link href="/dashboard" className="button" style={{ background: "rgba(148, 163, 184, 0.16)" }}>
              Lihat Dasbor
            </Link>
          </div>
        </div>
      </section>
    </main>
  );
}
