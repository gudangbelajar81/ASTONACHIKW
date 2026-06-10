"use client";

import { FormEvent, useEffect, useState } from "react";
import Sidebar from "../../components/Sidebar";
import { useTicker } from "../../context/TickerContext";
import { getApiBaseUrl } from "../../lib/apiBase";

const API_BASE_URL = getApiBaseUrl();

/* ── Types ────────────────────────────────────────────────────────────────── */
type TradeResult = {
  entry_date: string;
  exit_date: string;
  entry_price: number;
  exit_price: number;
  return_pct: number;
  score: number;
  exit_reason: string;
};

type BacktestResponse = {
  ticker: string;
  total_trade: number;
  win_rate: number | null;
  average_return: number | null;
  max_drawdown: number | null;
  expectancy: number | null;
  profit_factor: number | null;
  best_trade: TradeResult | null;
  worst_trade: TradeResult | null;
  threshold_checks: {
    threshold: number;
    trade_count: number;
    win_rate: number | null;
    average_forward_return: number | null;
    random_average_return: number | null;
    better_than_random: boolean | null;
  }[];
  benchmark: {
    symbol: string;
    strategy_total_return: number;
    benchmark_return: number | null;
    beats_benchmark: boolean | null;
  };
  trades: TradeResult[];
};

type ScreenerItem = {
  symbol: string;
  final_score: number;
  final_weighted_score?: number;
  signal: string;
  horizon: string;
  last_price: number;
  entry_zone: number[];
  target_1: number;
  stop_loss: number;
  risk_reward: number;
  avg_volume_20d: number;
  avg_value_20d: number;
  volume_ratio_5d: number;
  relative_strength: number;
  bandarmology: string;
  reasons: string[];
  risks: string[];
  /* Lapis 5: News Sentiment */
  news_sentiment_score?: number;
  news_sentiment_label?: "positive" | "neutral" | "negative";
  news_headlines?: string[];
  news_headline_count?: number;
};

type ScreenerResponse = {
  horizon: string;
  universe_size: number;
  scanned_size: number;
  total_daily?: number;
  total_weekly?: number;
  total_monthly?: number;
  top_daily: ScreenerItem[];
  top_weekly: ScreenerItem[];
  top_monthly: ScreenerItem[];
  avoid_high_risk: ScreenerItem[];
  gorengan_watchlist?: ScreenerItem[];
  news_data_available?: boolean;
  news_weighting_note?: string;
};

type SortMode = "weighted" | "technical" | "sentiment";
type SentimentFilter = "all" | "positive" | "neutral" | "negative";

/* ── Helpers ──────────────────────────────────────────────────────────────── */
function formatPercent(value: number | null | undefined) {
  if (value === null || value === undefined) return "--";
  return `${(value * 100).toFixed(2)}%`;
}

function formatNumber(value: number | null | undefined) {
  if (value === null || value === undefined) return "--";
  return new Intl.NumberFormat("id-ID", { maximumFractionDigits: 2 }).format(value);
}

function formatValue(value: number) {
  if (value >= 1_000_000_000) return `${(value / 1_000_000_000).toFixed(1)}M`;
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}Jt`;
  return formatNumber(value);
}

function sentimentBadge(label: string | undefined) {
  if (label === "positive") return { icon: "🟢", text: "Positif", cls: "sentiment-pos" };
  if (label === "negative") return { icon: "🔴", text: "Negatif", cls: "sentiment-neg" };
  return { icon: "🟡", text: "Netral", cls: "sentiment-neu" };
}

function sortItems(items: ScreenerItem[], mode: SortMode): ScreenerItem[] {
  const sorted = [...items];
  if (mode === "weighted") sorted.sort((a, b) => (b.final_weighted_score ?? b.final_score) - (a.final_weighted_score ?? a.final_score));
  if (mode === "technical") sorted.sort((a, b) => b.final_score - a.final_score);
  if (mode === "sentiment") sorted.sort((a, b) => (b.news_sentiment_score ?? 0.5) - (a.news_sentiment_score ?? 0.5));
  return sorted;
}

function filterBySentiment(items: ScreenerItem[], filter: SentimentFilter): ScreenerItem[] {
  if (filter === "all") return items;
  return items.filter((item) => (item.news_sentiment_label ?? "neutral") === filter);
}

/* ── Sub-component: Kartu Screener ───────────────────────────────────────── */
function ScreenerCard({ item }: { item: ScreenerItem }) {
  const [expanded, setExpanded] = useState(false);
  const badge = sentimentBadge(item.news_sentiment_label);

  return (
    <article className="workflow-card screener-card">
      {/* Header */}
      <div className="workflow-card__topline">
        <div>
          <h2>{item.symbol}</h2>
          <p>
            {item.signal} • Teknikal:{" "}
            <strong>{item.final_score}</strong>
            {item.final_weighted_score !== undefined && (
              <> • Gabungan: <strong>{item.final_weighted_score.toFixed(1)}</strong></>
            )}
            {" "}• {item.bandarmology}
          </p>
        </div>
        <div className="screener-card__badges">
          <span className={`sentiment-badge ${badge.cls}`}>
            {badge.icon} {badge.text}
          </span>
          <span className="prediction-signal prediction-signal--bullish">
            {item.risk_reward.toFixed(2)}x
          </span>
        </div>
      </div>

      {/* Metrics */}
      <div className="workflow-levels">
        <div><span>Entry</span><strong>{formatNumber(item.entry_zone[0])} – {formatNumber(item.entry_zone[1])}</strong></div>
        <div><span>Target</span><strong>{formatNumber(item.target_1)}</strong></div>
        <div><span>Stop</span><strong>{formatNumber(item.stop_loss)}</strong></div>
        <div><span>RS vs IHSG</span><strong>{formatPercent(item.relative_strength)}</strong></div>
        <div><span>Nilai 20H</span><strong>{formatValue(item.avg_value_20d)}</strong></div>
        <div><span>Vol Ratio</span><strong>{item.volume_ratio_5d.toFixed(2)}x</strong></div>
      </div>

      {/* Alasan */}
      <div className="workflow-reasons">
        <ul>{item.reasons.slice(0, 3).map((r) => <li key={r}>{r}</li>)}</ul>
      </div>

      {/* Berita — expandable */}
      {(item.news_headlines?.length ?? 0) > 0 && (
        <div className="news-section">
          <button
            type="button"
            className="news-toggle"
            onClick={() => setExpanded((prev) => !prev)}
          >
            📰 {item.news_headline_count ?? item.news_headlines!.length} Berita Terkini{" "}
            {expanded ? "▲" : "▼"}
          </button>
          {expanded && (
            <ul className="news-list">
              {item.news_headlines!.map((headline, idx) => (
                <li key={idx}>{headline}</li>
              ))}
            </ul>
          )}
        </div>
      )}
    </article>
  );
}

/* ── Sub-component: Daftar Screener ──────────────────────────────────────── */
function ScreenerList({
  title,
  items,
  sortMode,
  sentimentFilter,
}: {
  title: string;
  items: ScreenerItem[];
  sortMode: SortMode;
  sentimentFilter: SentimentFilter;
}) {
  const displayed = filterBySentiment(sortItems(items, sortMode), sentimentFilter);

  return (
    <section className="workflow-card">
      <div className="workflow-card__topline">
        <div>
          <h2>{title}</h2>
          <p>
            {displayed.length} saham ditampilkan
            {sentimentFilter !== "all" ? ` (filter: ${sentimentFilter})` : ""}
            {items.length !== displayed.length ? ` dari ${items.length} total lolos` : ""}
          </p>
        </div>
      </div>
      {displayed.length ? (
        displayed.map((item) => <ScreenerCard key={`${title}-${item.symbol}`} item={item} />)
      ) : (
        <div className="api-empty">
          Tidak ada saham yang lolos filter{sentimentFilter !== "all" ? ` sentimen "${sentimentFilter}"` : ""}.
        </div>
      )}
    </section>
  );
}

/* ── Halaman Utama ────────────────────────────────────────────────────────── */
export default function BacktestPage() {
  const { globalTicker, setGlobalTicker } = useTicker();
  const currentTicker = globalTicker || "BBCA";
  const [ticker, setTicker] = useState(currentTicker);

  useEffect(() => {
    if (globalTicker) setTicker(globalTicker);
  }, [globalTicker]);

  const [startDate, setStartDate] = useState("2024-01-01");
  const [endDate, setEndDate] = useState(new Date().toISOString().slice(0, 10));
  const [horizon, setHorizon] = useState("5d");
  const [ruleEntry, setRuleEntry] = useState("score_gt_70");
  const [backtest, setBacktest] = useState<BacktestResponse | null>(null);
  const [screener, setScreener] = useState<ScreenerResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  /* Filter & Sort state */
  const [sortMode, setSortMode] = useState<SortMode>("weighted");
  const [sentimentFilter, setSentimentFilter] = useState<SentimentFilter>("all");
  const [activeTab, setActiveTab] = useState<"daily" | "weekly" | "monthly" | "avoid" | "gorengan">("daily");

  async function runBacktest(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (ticker) setGlobalTicker(ticker);
    setLoading(true);
    setError("");
    try {
      const response = await fetch(`${API_BASE_URL}/api/idx/backtest`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ticker,
          start_date: startDate,
          end_date: endDate,
          horizon,
          rule_entry: ruleEntry,
          rule_exit: "target_stop_or_horizon",
          stop_loss: 0.03,
          target_profit: 0.06,
        }),
      });
      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(body?.detail ?? "Backtest gagal.");
      }
      setBacktest((await response.json()) as BacktestResponse);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Backtest gagal.");
    } finally {
      setLoading(false);
    }
  }

  async function runScreener() {
    setLoading(true);
    setError("");
    setScreener(null);
    try {
      const horizonLabel = horizon === "1d" ? "daily" : horizon === "20d" ? "monthly" : "weekly";
      const response = await fetch(`${API_BASE_URL}/api/run-idx-screener`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          horizon: horizonLabel,
          min_volume: 1_000_000,
          min_value: 5_000_000_000,
          top_n: 0,          // 0 = tampilkan semua yang lolos
        }),
      });
      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(body?.detail ?? "Screener gagal.");
      }
      setScreener((await response.json()) as ScreenerResponse);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Screener gagal.");
    } finally {
      setLoading(false);
    }
  }

  /* ── Render ─────────────────────────────────────────────────────────────── */
  return (
    <div className="dashboard-shell">
      <Sidebar />
      <main className="dashboard-main">
        {/* Header */}
        <div className="dashboard-header">
          <div>
            <p className="dashboard-eyebrow">IDX Research</p>
            <h1>Backtest &amp; Screener</h1>
            <p className="page-subtitle">
              Uji rule sebelum ranking saham. Semua saham yang lolos kriteria ditampilkan
              dan diurutkan berdasarkan <strong>75% Skor Teknikal + 25% Sentimen Berita</strong>.
            </p>
          </div>
          <button type="button" onClick={runScreener} disabled={loading}>
            {loading ? "⏳ Memproses..." : "🔍 Run Screener"}
          </button>
        </div>

        {/* Backtest Form */}
        <form className="watchlist-form workflow-form" onSubmit={runBacktest}>
          <input value={ticker} onChange={(e) => setTicker(e.target.value)} placeholder="BBCA" />
          <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
          <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
          <select value={horizon} onChange={(e) => setHorizon(e.target.value)}>
            <option value="1d">1d</option>
            <option value="5d">5d</option>
            <option value="20d">20d</option>
          </select>
          <select value={ruleEntry} onChange={(e) => setRuleEntry(e.target.value)}>
            <option value="score_gt_70">Score &gt; 70</option>
            <option value="score_gt_80">Score &gt; 80</option>
            <option value="ma20_gt_ma50">MA20 &gt; MA50</option>
            <option value="breakout">Near Breakout</option>
          </select>
          <button type="submit" disabled={loading}>{loading ? "Memproses" : "Run Backtest"}</button>
        </form>

        {error ? <div className="dashboard-alert">{error}</div> : null}

        {/* Backtest summary */}
        <section className="workflow-summary">
          <div className="metric-card"><span>Total Trade</span><strong>{backtest?.total_trade ?? "--"}</strong></div>
          <div className="metric-card"><span>Win Rate</span><strong>{formatPercent(backtest?.win_rate)}</strong></div>
          <div className="metric-card"><span>Avg Return</span><strong>{formatPercent(backtest?.average_return)}</strong></div>
          <div className="metric-card"><span>Profit Factor</span><strong>{formatNumber(backtest?.profit_factor)}</strong></div>
        </section>

        {backtest ? (
          <section className="workflow-card">
            <div className="workflow-card__topline">
              <div>
                <h2>{backtest.ticker} Backtest</h2>
                <p>Expectancy {formatPercent(backtest.expectancy)} • Max DD {formatPercent(backtest.max_drawdown)}</p>
              </div>
              <span className="prediction-signal prediction-signal--netral">
                {backtest.benchmark.beats_benchmark === null ? "No IHSG" : backtest.benchmark.beats_benchmark ? "Beat IHSG ✓" : "Below IHSG"}
              </span>
            </div>
            <div className="workflow-timeframes">
              {backtest.threshold_checks.map((check) => (
                <div key={check.threshold}>
                  <span>Score &gt; {check.threshold}</span>
                  <strong>{check.better_than_random === null ? "--" : check.better_than_random ? "Lebih baik" : "Belum unggul"}</strong>
                  <p>Win rate {formatPercent(check.win_rate)} • Avg {formatPercent(check.average_forward_return)} • Random {formatPercent(check.random_average_return)}</p>
                </div>
              ))}
            </div>
          </section>
        ) : null}

        {/* Screener Results */}
        {screener ? (
          <>
            {/* Info bar */}
            <section className="screener-info-bar">
              <div className="screener-stats">
                <span>🔭 Universe: <strong>{screener.universe_size} saham</strong></span>
                <span>✅ Lolos Harian: <strong>{screener.total_daily ?? screener.top_daily.length}</strong></span>
                <span>✅ Lolos Mingguan: <strong>{screener.total_weekly ?? screener.top_weekly.length}</strong></span>
                <span>✅ Lolos Bulanan: <strong>{screener.total_monthly ?? screener.top_monthly.length}</strong></span>
                {screener.news_data_available && (
                  <span className="news-badge-active">📰 Sentimen Berita Aktif</span>
                )}
              </div>
              {screener.news_weighting_note && (
                <p className="screener-note">{screener.news_weighting_note}</p>
              )}
            </section>

            {/* Filter & Sort controls */}
            <section className="screener-controls">
              <div className="screener-controls__group">
                <label>Urutkan:</label>
                <div className="sort-buttons">
                  <button
                    type="button"
                    className={sortMode === "weighted" ? "sort-btn active" : "sort-btn"}
                    onClick={() => setSortMode("weighted")}
                  >
                    ⚖️ Skor Gabungan
                  </button>
                  <button
                    type="button"
                    className={sortMode === "technical" ? "sort-btn active" : "sort-btn"}
                    onClick={() => setSortMode("technical")}
                  >
                    📊 Skor Teknikal
                  </button>
                  <button
                    type="button"
                    className={sortMode === "sentiment" ? "sort-btn active" : "sort-btn"}
                    onClick={() => setSortMode("sentiment")}
                  >
                    📰 Sentimen Berita
                  </button>
                </div>
              </div>

              <div className="screener-controls__group">
                <label>Filter Sentimen:</label>
                <div className="sort-buttons">
                  {(["all", "positive", "neutral", "negative"] as SentimentFilter[]).map((f) => (
                    <button
                      key={f}
                      type="button"
                      className={sentimentFilter === f ? "sort-btn active" : "sort-btn"}
                      onClick={() => setSentimentFilter(f)}
                    >
                      {f === "all" ? "Semua" : f === "positive" ? "🟢 Positif" : f === "neutral" ? "🟡 Netral" : "🔴 Negatif"}
                    </button>
                  ))}
                </div>
              </div>
            </section>

            {/* Tab navigation */}
            <div className="screener-tabs">
              {[
                { key: "daily", label: `📅 Harian (${screener.total_daily ?? screener.top_daily.length})` },
                { key: "weekly", label: `📆 Mingguan (${screener.total_weekly ?? screener.top_weekly.length})` },
                { key: "monthly", label: `🗓️ Bulanan (${screener.total_monthly ?? screener.top_monthly.length})` },
                { key: "avoid", label: `⚠️ Hindari (${screener.avoid_high_risk.length})` },
                { key: "gorengan", label: `🔥 Gorengan (${screener.gorengan_watchlist?.length ?? 0})` },
              ].map((tab) => (
                <button
                  key={tab.key}
                  type="button"
                  className={activeTab === tab.key ? "screener-tab active" : "screener-tab"}
                  onClick={() => setActiveTab(tab.key as typeof activeTab)}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            {/* Tab content */}
            {activeTab === "daily" && (
              <ScreenerList title="Saham Harian" items={screener.top_daily} sortMode={sortMode} sentimentFilter={sentimentFilter} />
            )}
            {activeTab === "weekly" && (
              <ScreenerList title="Saham Mingguan" items={screener.top_weekly} sortMode={sortMode} sentimentFilter={sentimentFilter} />
            )}
            {activeTab === "monthly" && (
              <ScreenerList title="Saham Bulanan" items={screener.top_monthly} sortMode={sortMode} sentimentFilter={sentimentFilter} />
            )}
            {activeTab === "avoid" && (
              <ScreenerList title="⚠️ Daftar Hindari" items={screener.avoid_high_risk} sortMode={sortMode} sentimentFilter={sentimentFilter} />
            )}
            {activeTab === "gorengan" && screener.gorengan_watchlist && (
              <ScreenerList title="🔥 Watchlist Gorengan (WASPADA)" items={screener.gorengan_watchlist} sortMode={sortMode} sentimentFilter={sentimentFilter} />
            )}
          </>
        ) : null}
      </main>
    </div>
  );
}
