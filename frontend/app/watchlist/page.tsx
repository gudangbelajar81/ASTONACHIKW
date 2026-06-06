"use client";

import { FormEvent, useEffect, useState } from "react";
import Sidebar from "../../components/Sidebar";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "https://astonachikw-production.up.railway.app";

type WatchlistItem = {
  ticker: string;
  signal: string;
  probability_up: number;
  confidence: string;
  expected_return: number;
  risk_label: string;
  regime: string;
  sentiment: string;
  risk_budget: string;
};

function formatPercent(value: number) {
  return `${(value * 100).toFixed(1)}%`;
}

export default function WatchlistPage() {
  const [input, setInput] = useState("AAPL,MSFT,NVDA,GOOGL,AMZN,META,TSLA");
  const [tickers, setTickers] = useState(input);
  const [items, setItems] = useState<WatchlistItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function loadWatchlist(nextTickers: string) {
    setLoading(true);
    setError("");
    try {
      const response = await fetch(`${API_BASE_URL}/api/watchlist?tickers=${encodeURIComponent(nextTickers)}&horizon_days=30`);
      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(body?.detail ?? `${response.status} ${response.statusText}`);
      }
      const data = await response.json();
      setItems(data.items ?? []);
    } catch (exc) {
      setItems([]);
      setError(exc instanceof Error ? exc.message : "Gagal membaca watchlist.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadWatchlist(tickers);
  }, [tickers]);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setTickers(input);
  }

  return (
    <div className="dashboard-shell">
      <Sidebar />
      <main className="dashboard-main">
        <div className="dashboard-header">
          <div>
            <p className="dashboard-eyebrow">Watchlist</p>
            <h1>Ranking Peluang</h1>
          </div>
          <form className="watchlist-form" onSubmit={handleSubmit}>
            <input value={input} onChange={(event) => setInput(event.target.value)} />
            <button type="submit" disabled={loading}>
              {loading ? "Memuat" : "Scan"}
            </button>
          </form>
        </div>

        {error ? <div className="dashboard-alert">{error}</div> : null}

        <section className="watchlist-table">
          <div className="watchlist-row watchlist-row--head">
            <span>Ticker</span>
            <span>Signal</span>
            <span>Prob. Naik</span>
            <span>Return</span>
            <span>Regime</span>
            <span>Risk</span>
          </div>
          {items.length ? (
            items.map((item) => (
              <div className="watchlist-row" key={item.ticker}>
                <strong>{item.ticker}</strong>
                <span className={`prediction-signal prediction-signal--${item.signal}`}>{item.signal}</span>
                <span>{formatPercent(item.probability_up)}</span>
                <span>{formatPercent(item.expected_return)}</span>
                <span>{item.regime}</span>
                <span>{item.risk_budget}</span>
              </div>
            ))
          ) : (
            <div className="api-empty">{loading ? "Memindai watchlist..." : "Belum ada hasil ranking."}</div>
          )}
        </section>
      </main>
    </div>
  );
}
