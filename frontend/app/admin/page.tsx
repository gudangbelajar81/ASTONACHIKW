"use client";

import { useEffect, useState } from "react";
import Sidebar from "../../components/Sidebar";
import type { ReportLog } from "../../lib/userData";
import { readAlerts, readPortfolio, readReportHistory, readSavedWatchlists } from "../../lib/userData";
import { readApiProviders, readMarketProviders } from "../../lib/apiKeys";

type AdminSnapshot = {
  alerts: number;
  enabledAlerts: number;
  portfolioHoldings: number;
  savedWatchlists: number;
  reportHistory: number;
  aiProviders: number;
  liveKeys: number;
  deadKeys: number;
  unknownKeys: number;
  marketProviders: number;
  enabledMarketProviders: number;
};

function formatDate(value: string) {
  return new Date(value).toLocaleString("id-ID", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function AdminPage() {
  const [snapshot, setSnapshot] = useState<AdminSnapshot | null>(null);
  const [lastRefresh, setLastRefresh] = useState<string>("");
  const [reports, setReports] = useState<ReportLog[]>([]);

  function refresh() {
    const alerts = readAlerts();
    const holdings = readPortfolio();
    const watchlists = readSavedWatchlists();
    const apiProviders = readApiProviders();
    const marketProviders = readMarketProviders();
    const keys = apiProviders.flatMap((provider) => provider.keys);

    setSnapshot({
      alerts: alerts.length,
      enabledAlerts: alerts.filter((item) => item.enabled).length,
      portfolioHoldings: holdings.length,
      savedWatchlists: watchlists.length,
      reportHistory: readReportHistory().length,
      aiProviders: apiProviders.length,
      liveKeys: keys.filter((key) => key.status === "live").length,
      deadKeys: keys.filter((key) => key.status === "dead").length,
      unknownKeys: keys.filter((key) => key.status === "unknown").length,
      marketProviders: marketProviders.length,
      enabledMarketProviders: marketProviders.filter((provider) => provider.enabled).length,
    });
    setReports(readReportHistory());
    setLastRefresh(new Date().toISOString());
  }

  useEffect(() => {
    refresh();
  }, []);

  return (
    <div className="dashboard-shell">
      <Sidebar />
      <main className="dashboard-main">
        <div className="dashboard-header">
          <div>
            <p className="dashboard-eyebrow">Admin</p>
            <h1>Control Center</h1>
            <p className="page-subtitle">Ringkasan data lokal pengguna, provider, dan riwayat laporan.</p>
          </div>
          <button className="action-button" type="button" onClick={refresh}>
            Refresh
          </button>
        </div>

        {snapshot ? (
          <section className="admin-grid">
            <div className="admin-stat">
              <span>Alerts</span>
              <strong>{snapshot.alerts}</strong>
              <p>{snapshot.enabledAlerts} aktif</p>
            </div>
            <div className="admin-stat">
              <span>Portfolio</span>
              <strong>{snapshot.portfolioHoldings}</strong>
              <p>holding tersimpan</p>
            </div>
            <div className="admin-stat">
              <span>Saved Watchlists</span>
              <strong>{snapshot.savedWatchlists}</strong>
              <p>daftar tersimpan</p>
            </div>
            <div className="admin-stat">
              <span>Report History</span>
              <strong>{snapshot.reportHistory}</strong>
              <p>laporan dibuat</p>
            </div>
            <div className="admin-stat">
              <span>AI Keys</span>
              <strong>{snapshot.aiProviders}</strong>
              <p>{snapshot.liveKeys} live, {snapshot.deadKeys} dead, {snapshot.unknownKeys} belum cek</p>
            </div>
            <div className="admin-stat">
              <span>IDX Providers</span>
              <strong>{snapshot.marketProviders}</strong>
              <p>{snapshot.enabledMarketProviders} aktif</p>
            </div>
          </section>
        ) : null}

        <section className="admin-panels">
          <article className="utility-card">
            <h2>Status Sistem Lokal</h2>
            <p>
              Semua data di panel ini dibaca dari browser pengguna, jadi cocok untuk memantau konfigurasi,
              riwayat, dan kesehatan fitur tanpa harus menunggu backend.
            </p>
            {lastRefresh ? <p>Terakhir diperbarui: {formatDate(lastRefresh)}</p> : null}
          </article>

          <article className="utility-card">
            <h2>Riwayat Report</h2>
            {reports.length ? (
              <div className="admin-report-list">
                {reports.slice(0, 8).map((entry) => (
                  <div key={entry.id} className="admin-report-row">
                    <span>{entry.ticker}</span>
                    <strong>{entry.signal}</strong>
                    <span>{entry.regime}</span>
                    <span>{entry.confidence}</span>
                    <time>{formatDate(entry.generatedAt)}</time>
                  </div>
                ))}
              </div>
            ) : (
              <p>Belum ada report yang digenerate.</p>
            )}
          </article>
        </section>
      </main>
    </div>
  );
}
