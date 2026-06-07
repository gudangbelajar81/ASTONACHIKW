"use client";

import { FormEvent, useEffect, useState } from "react";
import Sidebar from "../../components/Sidebar";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "https://astonachikw-production.up.railway.app";

type Prediction = {
  ticker: string;
  signal: string;
  probability_up: number;
  confidence: string;
  expected_return: number;
  risk_label: string;
  factors: { name: string; value: number; weight: number; contribution: number; description: string }[];
  regime: { label: string; description: string; trend_score: number; volatility_score: number; momentum_score: number };
  sentiment?: { label: string; score: number; description: string } | null;
  macro?: { risk_budget: string; beta: number; correlation: number; relative_strength: number; description: string } | null;
  scenario?: { playbook: string; entry_zone_low: number; entry_zone_high: number; invalidation_level: number } | null;
};

function formatPercent(value: number) {
  return `${(value * 100).toFixed(1)}%`;
}

export default function ExplainPage() {
  const [tickerInput, setTickerInput] = useState("AAPL");
  const [ticker, setTicker] = useState("AAPL");
  const [prediction, setPrediction] = useState<Prediction | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function loadPrediction(nextTicker: string) {
    setLoading(true);
    setError("");
    try {
      const response = await fetch(`${API_BASE_URL}/api/predictions/${encodeURIComponent(nextTicker)}?horizon_days=30`);
      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(body?.detail ?? `${response.status} ${response.statusText}`);
      }
      setPrediction((await response.json()) as Prediction);
    } catch (exc) {
      setPrediction(null);
      setError(exc instanceof Error ? exc.message : "Gagal membaca explainability.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadPrediction(ticker);
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
            <p className="dashboard-eyebrow">Explain</p>
            <h1>Model Explainability</h1>
          </div>
          <form className="ticker-form" onSubmit={handleSubmit}>
            <input value={tickerInput} onChange={(event) => setTickerInput(event.target.value)} />
            <button type="submit" disabled={loading}>{loading ? "Memuat" : "Jelaskan"}</button>
          </form>
        </div>

        {error ? <div className="dashboard-alert">{error}</div> : null}

        {prediction ? (
          <section className="explain-layout">
            <article className="performance-verdict">
              <div>
                <h2>{prediction.ticker}: {prediction.signal}</h2>
                <p>
                  Probabilitas naik {formatPercent(prediction.probability_up)}, expected return {formatPercent(prediction.expected_return)}, confidence {prediction.confidence}.
                </p>
              </div>
              <span className={`prediction-signal prediction-signal--${prediction.signal}`}>{prediction.signal}</span>
            </article>

            <article className="utility-card">
              <h2>Kontribusi Faktor</h2>
              {prediction.factors
                .slice()
                .sort((a, b) => Math.abs(b.contribution) - Math.abs(a.contribution))
                .map((factor) => (
                  <div className="explain-factor" key={factor.name}>
                    <div>
                      <strong>{factor.name}</strong>
                      <span>{factor.description}</span>
                    </div>
                    <span>{factor.contribution.toFixed(3)}</span>
                  </div>
                ))}
            </article>

            <article className="utility-card">
              <h2>Konteks Keputusan</h2>
              <div className="context-grid">
                <div><span>Regime</span><strong>{prediction.regime.label}</strong><p>{prediction.regime.description}</p></div>
                <div><span>Sentimen</span><strong>{prediction.sentiment?.label ?? "netral"}</strong><p>{prediction.sentiment?.description ?? "Tidak ada headline kuat."}</p></div>
                <div><span>Macro Risk</span><strong>{prediction.macro?.risk_budget ?? "normal"}</strong><p>{prediction.macro?.description ?? "Tidak ada konteks makro."}</p></div>
                <div><span>Risk Label</span><strong>{prediction.risk_label}</strong><p>Label risiko menyesuaikan volatility, regime, dan macro budget.</p></div>
              </div>
            </article>

            {prediction.scenario ? (
              <article className="utility-card">
                <h2>Rencana Aksi</h2>
                <p>{prediction.scenario.playbook}</p>
                <div className="scenario-panel">
                  <div><span>Entry Low</span><strong>{prediction.scenario.entry_zone_low}</strong></div>
                  <div><span>Entry High</span><strong>{prediction.scenario.entry_zone_high}</strong></div>
                  <div><span>Invalidation</span><strong>{prediction.scenario.invalidation_level}</strong></div>
                </div>
              </article>
            ) : null}
          </section>
        ) : loading ? (
          <div className="api-empty">Membaca penjelasan model...</div>
        ) : null}
      </main>
    </div>
  );
}
