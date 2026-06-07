"use client";

import Link from "next/link";
import { FormEvent, useEffect, useMemo, useState } from "react";
import Sidebar from "../../components/Sidebar";
import { normalizeTickerList, readMarketMode, writeMarketMode } from "../../lib/userData";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "https://astonachikw-production.up.railway.app";

type WorkflowFrame = {
  label: string;
  horizon_days: number;
  signal: string;
  probability_up: number;
  confidence: string;
  expected_return: number;
  risk_label: string;
  summary: string;
};

type WorkflowItem = {
  ticker: string;
  rank_score: number;
  recommended_action: string;
  entry_zone_low: number;
  entry_zone_high: number;
  target_price: number;
  stop_loss: number;
  reasons: string[];
  daily: WorkflowFrame;
  weekly: WorkflowFrame;
  monthly: WorkflowFrame;
  latest_prediction: {
    signal: string;
    probability_up: number;
    confidence: string;
    expected_return: number;
    risk_label: string;
    regime: { label: string; description: string };
    scenario?: {
      entry_zone_low: number;
      entry_zone_high: number;
      invalidation_level: number;
      bullish_target: number;
      bearish_target: number;
      position_size_shares: number;
      risk_amount: number;
      risk_per_share: number;
      playbook: string;
    } | null;
  };
};

type WorkflowResponse = {
  market: string;
  universe_size: number;
  scanned_size: number;
  items: WorkflowItem[];
};

function formatPercent(value: number) {
  return `${(value * 100).toFixed(1)}%`;
}

function formatCurrency(value: number) {
  return new Intl.NumberFormat("id-ID", { maximumFractionDigits: 2 }).format(value);
}

const PRESET_IDX = "BBCA,BBRI,BMRI,TLKM,ASII,BBNI,UNVR,CPIN,ICBP,AMRT";

export default function WorkflowPage() {
  const [input, setInput] = useState(PRESET_IDX);
  const [tickers, setTickers] = useState(PRESET_IDX);
  const [market, setMarket] = useState<"id" | "us">("id");
  const [report, setReport] = useState<WorkflowResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    setMarket(readMarketMode());
  }, []);

  async function loadWorkflow(nextTickers: string, nextMarket: "id" | "us") {
    setLoading(true);
    setError("");
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/workflow/idx?tickers=${encodeURIComponent(nextTickers)}&market=${nextMarket}`
      );
      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(body?.detail ?? `${response.status} ${response.statusText}`);
      }
      setReport((await response.json()) as WorkflowResponse);
    } catch (exc) {
      setReport(null);
      setError(exc instanceof Error ? exc.message : "Gagal membaca workflow IDX.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    const initialMarket = readMarketMode();
    setMarket(initialMarket);
    const normalized = normalizeTickerList(PRESET_IDX, initialMarket).join(",");
    setInput(PRESET_IDX);
    setTickers(normalized);
    void loadWorkflow(normalized, initialMarket);
  }, []);

  function applyMarket(nextMarket: "id" | "us") {
    setMarket(nextMarket);
    writeMarketMode(nextMarket);
    const normalized = normalizeTickerList(input, nextMarket).join(",");
    setTickers(normalized);
    void loadWorkflow(normalized, nextMarket);
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalized = normalizeTickerList(input, market).join(",");
    setTickers(normalized);
    void loadWorkflow(normalized, market);
  }

  const topTicker = useMemo(() => report?.items[0], [report]);

  return (
    <div className="dashboard-shell">
      <Sidebar />
      <main className="dashboard-main">
        <div className="dashboard-header">
          <div>
            <p className="dashboard-eyebrow">IDX Workflow</p>
            <h1>Filter Multi-Horizon</h1>
            <p className="page-subtitle">
              Mesin menyaring saham IDX dengan prediksi harian, mingguan, dan bulanan, lalu memberi entry, target, dan stop loss.
            </p>
          </div>
          <div className="workflow-toolbar">
            <button
              type="button"
            className={market === "id" ? "active" : ""}
            onClick={() => applyMarket("id")}
          >
            IDX / Indonesia
          </button>
          <button
            type="button"
            className={market === "us" ? "active" : ""}
            onClick={() => applyMarket("us")}
          >
            US Market
          </button>
          </div>
        </div>

        <form className="watchlist-form workflow-form" onSubmit={handleSubmit}>
          <input value={input} onChange={(event) => setInput(event.target.value)} />
          <button type="submit" disabled={loading}>
            {loading ? "Memuat" : "Saring"}
          </button>
          <button
            type="button"
            className="watchlist-savebar__ghost"
            onClick={() => setInput(PRESET_IDX)}
          >
            Preset IDX
          </button>
        </form>

        {error ? <div className="dashboard-alert">{error}</div> : null}

        <section className="workflow-summary">
          <div className="metric-card">
            <span>Universe</span>
            <strong>{report?.universe_size ?? 0}</strong>
          </div>
          <div className="metric-card">
            <span>Lolos Scan</span>
            <strong>{report?.scanned_size ?? 0}</strong>
          </div>
          <div className="metric-card">
            <span>Top Rank</span>
            <strong>{topTicker?.ticker ?? "--"}</strong>
          </div>
          <div className="metric-card">
            <span>Aksi Teratas</span>
            <strong>{topTicker?.recommended_action ?? "--"}</strong>
          </div>
        </section>

        <section className="workflow-list">
          {report?.items.length ? (
            report.items.map((item) => (
              <article className="workflow-card" key={item.ticker}>
                <div className="workflow-card__topline">
                  <div>
                    <h2>{item.ticker}</h2>
                    <p>
                      Rank score {item.rank_score.toFixed(3)} • {item.recommended_action}
                    </p>
                  </div>
                  <span className={`prediction-signal prediction-signal--${item.latest_prediction.signal}`}>
                    {item.latest_prediction.signal}
                  </span>
                </div>

                <div className="workflow-levels">
                  <div>
                    <span>Entry</span>
                    <strong>
                      {formatCurrency(item.entry_zone_low)} - {formatCurrency(item.entry_zone_high)}
                    </strong>
                  </div>
                  <div>
                    <span>Target</span>
                    <strong>{formatCurrency(item.target_price)}</strong>
                  </div>
                  <div>
                    <span>Stop Loss</span>
                    <strong>{formatCurrency(item.stop_loss)}</strong>
                  </div>
                </div>

                <div className="workflow-timeframes">
                  {[item.daily, item.weekly, item.monthly].map((frame) => (
                    <div key={frame.label}>
                      <span>{frame.label}</span>
                      <strong>{frame.signal}</strong>
                      <p>
                        {formatPercent(frame.probability_up)} naik • {frame.confidence} • {frame.risk_label}
                      </p>
                      <p>{frame.summary}</p>
                    </div>
                  ))}
                </div>

                <div className="workflow-reasons">
                  <h3>Alasan</h3>
                  <ul>
                    {item.reasons.map((reason) => (
                      <li key={reason}>{reason}</li>
                    ))}
                  </ul>
                </div>
              </article>
            ))
          ) : (
            <div className="api-empty">{loading ? "Menyaring saham IDX..." : "Belum ada hasil workflow."}</div>
          )}
        </section>
      </main>
    </div>
  );
}
