"use client";

import Link from "next/link";
import { FormEvent, useEffect, useMemo, useState } from "react";
import Sidebar from "../../components/Sidebar";
import { buildMarketProviderConfig, readMarketProviders } from "../../lib/apiKeys";
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

type RecommendationResponse = {
  symbol: string;
  market: string;
  horizon: string;
  final_score: number;
  signal: string;
  confidence: number;
  last_price: number;
  entry_zone: number[];
  target_1: number;
  target_2: number;
  stop_loss: number;
  risk_reward: number;
  score_breakdown: Record<string, number>;
  main_reasons: string[];
  main_risks: string[];
  price_context: {
    ma20?: number | null;
    ma50?: number | null;
    ma200?: number | null;
    support: number;
    resistance: number;
    volume_ratio_5d: number;
    relative_strength: number;
  };
  data_quality: {
    ohlcv_available: boolean;
    bandarmology_available: boolean;
    macro_available: boolean;
    fundamental_available: boolean;
  };
  validation: {
    sample_size: number;
    max_drawdown?: number | null;
    last_updated: string;
  };
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
  const [recommendation, setRecommendation] = useState<RecommendationResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [recommendationLoading, setRecommendationLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    setMarket(readMarketMode());
  }, []);

  async function loadRecommendation(ticker: string, nextMarket: "id" | "us") {
    setRecommendationLoading(true);
    try {
      const providerConfig = buildMarketProviderConfig(readMarketProviders());
      const response = await fetch(`${API_BASE_URL}/api/recommendations/idx`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ticker,
          horizon: "weekly",
          market: nextMarket,
          market_data_providers: providerConfig.market_data_providers,
        }),
      });
      if (!response.ok) {
        throw new Error("Gagal membaca rekomendasi terstruktur.");
      }
      setRecommendation((await response.json()) as RecommendationResponse);
    } catch {
      setRecommendation(null);
    } finally {
      setRecommendationLoading(false);
    }
  }

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
      const nextReport = (await response.json()) as WorkflowResponse;
      setReport(nextReport);
      const top = nextReport.items[0];
      if (top) {
        void loadRecommendation(top.ticker, nextMarket);
      } else {
        setRecommendation(null);
      }
    } catch (exc) {
      setReport(null);
      setRecommendation(null);
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

        <section className="workflow-card">
          <div className="workflow-card__topline">
            <div>
              <h2>Rekomendasi Terstruktur</h2>
              <p>
                {recommendation
                  ? `${recommendation.symbol} • ${recommendation.signal} • confidence ${formatPercent(recommendation.confidence)}`
                  : recommendationLoading
                    ? "Menghitung rekomendasi top rank..."
                    : "Belum ada rekomendasi terstruktur."}
              </p>
            </div>
            <span className="prediction-signal prediction-signal--bullish">
              {recommendation ? `${recommendation.final_score}/100` : "--"}
            </span>
          </div>

          {recommendation ? (
            <>
              <div className="workflow-levels">
                <div>
                  <span>Entry</span>
                  <strong>{formatCurrency(recommendation.entry_zone[0])} - {formatCurrency(recommendation.entry_zone[1])}</strong>
                </div>
                <div>
                  <span>Target 1 / 2</span>
                  <strong>{formatCurrency(recommendation.target_1)} / {formatCurrency(recommendation.target_2)}</strong>
                </div>
                <div>
                  <span>Stop Loss</span>
                  <strong>{formatCurrency(recommendation.stop_loss)}</strong>
                </div>
                <div>
                  <span>Risk/Reward</span>
                  <strong>{recommendation.risk_reward.toFixed(2)}x</strong>
                </div>
              </div>

              <div className="workflow-timeframes">
                {Object.entries(recommendation.score_breakdown).map(([key, value]) => (
                  <div key={key}>
                    <span>{key.replace("_", " ")}</span>
                    <strong>{value}</strong>
                  </div>
                ))}
              </div>

              <div className="workflow-reasons">
                <h3>Alasan Utama</h3>
                <ul>
                  {recommendation.main_reasons.map((reason) => <li key={reason}>{reason}</li>)}
                </ul>
                <h3>Risiko Utama</h3>
                <ul>
                  {recommendation.main_risks.map((risk) => <li key={risk}>{risk}</li>)}
                </ul>
              </div>
            </>
          ) : null}
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
