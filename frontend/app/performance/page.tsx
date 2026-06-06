"use client";

import { FormEvent, useEffect, useState } from "react";
import Sidebar from "../../components/Sidebar";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "https://astonachikw-production.up.railway.app";

type PerformanceReport = {
  ticker: string;
  horizon_days: number;
  verdict: string;
  backtest: {
    sample_count: number;
    hit_rate: number;
    average_forward_return: number;
    average_signal_return: number;
    max_drawdown: number;
  };
  latest_prediction: {
    signal: string;
    probability_up: number;
    confidence: string;
    expected_return: number;
    risk_label: string;
    as_of_date: string;
    regime: {
      label: string;
      trend_score: number;
      volatility_score: number;
      momentum_score: number;
      risk_multiplier: number;
      description: string;
    };
    sentiment?: {
      label: string;
      score: number;
      headline_count: number;
      description: string;
    } | null;
    macro?: {
      benchmark: string;
      beta: number;
      correlation: number;
      relative_strength: number;
      market_regime: string;
      risk_budget: string;
      description: string;
    } | null;
  };
  model_weights: {
    weights: Record<string, number>;
    sample_count: number;
    hit_rate: number;
    average_signal_return: number;
    method: string;
    trained_at: string | null;
  };
  snapshots: {
    as_of_date: string;
    signal: string;
    probability_up: number;
    confidence: string;
    expected_return: number | null;
    realized_return: number | null;
  }[];
};

function formatPercent(value: number | null | undefined) {
  if (value === null || value === undefined) return "--";
  return `${(value * 100).toFixed(1)}%`;
}

export default function PerformancePage() {
  const [tickerInput, setTickerInput] = useState("AAPL");
  const [ticker, setTicker] = useState("AAPL");
  const [report, setReport] = useState<PerformanceReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [training, setTraining] = useState(false);
  const [error, setError] = useState("");

  async function loadReport(nextTicker: string) {
    setLoading(true);
    setError("");
    try {
      const response = await fetch(`${API_BASE_URL}/api/performance/${encodeURIComponent(nextTicker)}?horizon_days=30`);
      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(body?.detail ?? `${response.status} ${response.statusText}`);
      }
      setReport((await response.json()) as PerformanceReport);
    } catch (exc) {
      setReport(null);
      setError(exc instanceof Error ? exc.message : "Gagal mengambil performance report.");
    } finally {
      setLoading(false);
    }
  }

  async function trainWeights() {
    setTraining(true);
    setError("");
    try {
      const response = await fetch(`${API_BASE_URL}/api/model-weights/${encodeURIComponent(ticker)}/train?horizon_days=30`, {
        method: "POST",
      });
      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(body?.detail ?? `${response.status} ${response.statusText}`);
      }
      await loadReport(ticker);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Gagal melatih ulang bobot model.");
    } finally {
      setTraining(false);
    }
  }

  useEffect(() => {
    void loadReport(ticker);
  }, [ticker]);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalizedTicker = tickerInput.trim().toUpperCase();
    if (normalizedTicker) setTicker(normalizedTicker);
  }

  return (
    <div className="dashboard-shell">
      <Sidebar />
      <main className="dashboard-main">
        <div className="dashboard-header">
          <div>
            <p className="dashboard-eyebrow">Performance</p>
            <h1>Performance Center</h1>
          </div>
          <form className="ticker-form" onSubmit={handleSubmit}>
            <input value={tickerInput} onChange={(event) => setTickerInput(event.target.value)} />
            <button type="submit" disabled={loading}>
              {loading ? "Memuat" : "Cek"}
            </button>
          </form>
        </div>

        {error ? <div className="dashboard-alert">{error}</div> : null}

        {report ? (
          <div className="performance-page">
            <section className="performance-verdict">
              <div>
                <h2>{report.ticker}</h2>
                <p>{report.verdict}</p>
              </div>
              <span className={`prediction-signal prediction-signal--${report.latest_prediction.signal}`}>
                {report.latest_prediction.signal}
              </span>
            </section>

            <section className="prediction-metrics">
              <div>
                <span>Hit Rate</span>
                <strong>{formatPercent(report.backtest.hit_rate)}</strong>
              </div>
              <div>
                <span>Return Sinyal</span>
                <strong>{formatPercent(report.backtest.average_signal_return)}</strong>
              </div>
              <div>
                <span>Max Drawdown</span>
                <strong>{formatPercent(report.backtest.max_drawdown)}</strong>
              </div>
              <div>
                <span>Sampel</span>
                <strong>{report.backtest.sample_count}</strong>
              </div>
            </section>

            <section className="performance-grid">
              <article className="performance-card">
                <h3>Prediksi Terbaru</h3>
                <p>
                  Probabilitas naik <strong>{formatPercent(report.latest_prediction.probability_up)}</strong>
                </p>
                <p>
                  Estimasi return <strong>{formatPercent(report.latest_prediction.expected_return)}</strong>
                </p>
                <p>
                  Confidence <strong>{report.latest_prediction.confidence}</strong>
                </p>
                <p>
                  Risiko <strong>{report.latest_prediction.risk_label}</strong>
                </p>
                <div className="regime-strip">
                  <div>
                    <span>Regime</span>
                    <strong>{report.latest_prediction.regime.label}</strong>
                  </div>
                  <p>{report.latest_prediction.regime.description}</p>
                </div>
                <div className="context-grid">
                  <div>
                    <span>Sentimen</span>
                    <strong>{report.latest_prediction.sentiment?.label ?? "netral"}</strong>
                    <p>{report.latest_prediction.sentiment?.description ?? "Belum ada headline kuat."}</p>
                  </div>
                  <div>
                    <span>Macro Risk</span>
                    <strong>{report.latest_prediction.macro?.risk_budget ?? "normal"}</strong>
                    <p>{report.latest_prediction.macro?.description ?? "Konteks benchmark belum tersedia."}</p>
                  </div>
                </div>
              </article>

              <article className="performance-card">
                <div className="performance-card__topline">
                  <h3>Bobot Model</h3>
                  <button type="button" onClick={trainWeights} disabled={training || loading}>
                    {training ? "Melatih..." : "Latih Ulang"}
                  </button>
                </div>
                <p>
                  Method <strong>{report.model_weights.method}</strong>
                </p>
                <p>
                  Hit rate training <strong>{formatPercent(report.model_weights.hit_rate)}</strong>
                </p>
                <div className="weight-list">
                  {Object.entries(report.model_weights.weights).map(([name, weight]) => (
                    <div key={name}>
                      <span>{name.replaceAll("_", " ")}</span>
                      <strong>{formatPercent(weight)}</strong>
                    </div>
                  ))}
                </div>
              </article>

              <article className="performance-card">
                <h3>Riwayat Snapshot</h3>
                {report.snapshots.length ? (
                  <div className="snapshot-table">
                    {report.snapshots.slice(0, 8).map((snapshot) => (
                      <div key={`${snapshot.as_of_date}-${snapshot.signal}`}>
                        <span>{snapshot.as_of_date}</span>
                        <strong>{snapshot.signal}</strong>
                        <span>{formatPercent(snapshot.probability_up)}</span>
                        <span>{formatPercent(snapshot.realized_return)}</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p>Belum ada snapshot tersimpan.</p>
                )}
              </article>
            </section>
          </div>
        ) : loading ? (
          <div className="api-empty">Mengambil performance report...</div>
        ) : null}
      </main>
    </div>
  );
}
