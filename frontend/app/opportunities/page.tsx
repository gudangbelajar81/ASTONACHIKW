"use client";

import { useEffect, useState } from "react";
import Sidebar from "../../components/Sidebar";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "https://astonachikw-production.up.railway.app";

type OpportunityItem = {
  symbol: string;
  final_score: number;
  signal: string;
  calibrated_probability?: number | null;
  horizon: string;
  last_price: number;
  entry_zone: number[];
  target_1: number;
  target_2: number;
  stop_loss: number;
  risk_reward: number;
  volume_ratio_5d: number;
  relative_strength: number;
  bandarmology: string;
  backtest_confidence?: string | null;
  backtest_win_rate?: number | null;
  backtest_profit_factor?: number | null;
  reasons: string[];
  risks: string[];
};

type OpportunityResponse = {
  horizon: string;
  universe_size: number;
  scanned_size: number;
  top_daily: OpportunityItem[];
  top_weekly: OpportunityItem[];
  top_monthly: OpportunityItem[];
  avoid_high_risk: OpportunityItem[];
};

function formatNumber(value: number) {
  return new Intl.NumberFormat("id-ID", { maximumFractionDigits: 2 }).format(value);
}

function formatPercent(value?: number | null) {
  if (value === null || value === undefined) return "--";
  return `${(value * 100).toFixed(1)}%`;
}

function OpportunityTable({ title, items }: { title: string; items: OpportunityItem[] }) {
  return (
    <section className="workflow-card">
      <div className="workflow-card__topline">
        <div>
          <h2>{title}</h2>
          <p>Score, entry, target, stop loss, risk/reward, alasan, risiko, dan confidence backtest.</p>
        </div>
      </div>
      {items.length ? (
        items.map((item) => (
          <article className="workflow-card" key={`${title}-${item.symbol}`}>
            <div className="workflow-card__topline">
              <div>
                <h2>{item.symbol}</h2>
                <p>
                  {item.signal} • calibrated probability {formatPercent(item.calibrated_probability)} • {item.bandarmology}
                </p>
              </div>
              <span className="prediction-signal prediction-signal--bullish">{item.final_score}/100</span>
            </div>
            <div className="workflow-levels">
              <div><span>Entry</span><strong>{formatNumber(item.entry_zone[0])} - {formatNumber(item.entry_zone[1])}</strong></div>
              <div><span>Target</span><strong>{formatNumber(item.target_1)} / {formatNumber(item.target_2)}</strong></div>
              <div><span>Stop Loss</span><strong>{formatNumber(item.stop_loss)}</strong></div>
              <div><span>R/R</span><strong>{item.risk_reward.toFixed(2)}x</strong></div>
              <div><span>Win Rate</span><strong>{formatPercent(item.backtest_win_rate)}</strong></div>
              <div><span>Profit Factor</span><strong>{item.backtest_profit_factor?.toFixed(2) ?? "--"}</strong></div>
              <div><span>Backtest</span><strong>{item.backtest_confidence ?? "--"}</strong></div>
            </div>
            <div className="workflow-timeframes">
              <div><span>Volume</span><strong>{item.volume_ratio_5d.toFixed(2)}x</strong></div>
              <div><span>RS vs IHSG</span><strong>{formatPercent(item.relative_strength)}</strong></div>
            </div>
            <div className="workflow-reasons">
              <h3>Alasan</h3>
              <ul>{item.reasons.slice(0, 4).map((reason) => <li key={reason}>{reason}</li>)}</ul>
              <h3>Risiko</h3>
              <ul>{item.risks.slice(0, 3).map((risk) => <li key={risk}>{risk}</li>)}</ul>
            </div>
          </article>
        ))
      ) : (
        <div className="api-empty">Belum ada saham yang lolos filter.</div>
      )}
    </section>
  );
}

export default function OpportunitiesPage() {
  const [report, setReport] = useState<OpportunityResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function loadRanking() {
    setLoading(true);
    setError("");
    try {
      const response = await fetch(`${API_BASE_URL}/api/run-idx-screener`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          horizon: "weekly",
          min_volume: 1000000,
          min_value: 5000000000,
          top_n: 20,
        }),
      });
      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(body?.detail ?? "Gagal membaca IDX Opportunity Ranking.");
      }
      setReport((await response.json()) as OpportunityResponse);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Gagal membaca IDX Opportunity Ranking.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadRanking();
  }, []);

  return (
    <div className="dashboard-shell">
      <Sidebar />
      <main className="dashboard-main">
        <div className="dashboard-header">
          <div>
            <p className="dashboard-eyebrow">IDX Opportunity</p>
            <h1>Opportunity Ranking</h1>
            <p className="page-subtitle">Ranking saham IDX berdasarkan scoring final, filter likuiditas, risk/reward, relative strength, bandarmology, dan confidence backtest.</p>
          </div>
          <button type="button" onClick={loadRanking} disabled={loading}>
            {loading ? "Memuat" : "Refresh"}
          </button>
        </div>

        {error ? <div className="dashboard-alert">{error}</div> : null}

        <section className="workflow-summary">
          <div className="metric-card"><span>Universe</span><strong>{report?.universe_size ?? "--"}</strong></div>
          <div className="metric-card"><span>Lolos Scan</span><strong>{report?.scanned_size ?? "--"}</strong></div>
          <div className="metric-card"><span>Top Harian</span><strong>{report?.top_daily.length ?? "--"}</strong></div>
          <div className="metric-card"><span>Top Mingguan</span><strong>{report?.top_weekly.length ?? "--"}</strong></div>
        </section>

        {report ? (
          <>
            <OpportunityTable title="Top 10 Saham Potensi Naik Harian" items={report.top_daily.slice(0, 10)} />
            <OpportunityTable title="Top 10 Saham Potensi Naik Mingguan" items={report.top_weekly.slice(0, 10)} />
            <OpportunityTable title="Top 10 Saham Potensi Naik Bulanan" items={report.top_monthly.slice(0, 10)} />
            <OpportunityTable title="Avoid / High Risk List" items={report.avoid_high_risk.slice(0, 10)} />
          </>
        ) : (
          <div className="api-empty">{loading ? "Menyusun ranking IDX..." : "Belum ada data ranking."}</div>
        )}
      </main>
    </div>
  );
}
