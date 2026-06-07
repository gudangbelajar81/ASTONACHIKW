"use client";

import { FormEvent, useState } from "react";
import Sidebar from "../../components/Sidebar";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "https://astonachikw-production.up.railway.app";

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
};

type ScreenerResponse = {
  horizon: string;
  universe_size: number;
  scanned_size: number;
  top_daily: ScreenerItem[];
  top_weekly: ScreenerItem[];
  top_monthly: ScreenerItem[];
  avoid_high_risk: ScreenerItem[];
};

function formatPercent(value: number | null | undefined) {
  if (value === null || value === undefined) return "--";
  return `${(value * 100).toFixed(2)}%`;
}

function formatNumber(value: number | null | undefined) {
  if (value === null || value === undefined) return "--";
  return new Intl.NumberFormat("id-ID", { maximumFractionDigits: 2 }).format(value);
}

function ScreenerList({ title, items }: { title: string; items: ScreenerItem[] }) {
  return (
    <section className="workflow-card">
      <div className="workflow-card__topline">
        <div>
          <h2>{title}</h2>
          <p>{items.length} saham</p>
        </div>
      </div>
      {items.length ? (
        items.map((item) => (
          <article className="workflow-card" key={`${title}-${item.symbol}`}>
            <div className="workflow-card__topline">
              <div>
                <h2>{item.symbol}</h2>
                <p>{item.signal} • score {item.final_score} • {item.bandarmology}</p>
              </div>
              <span className="prediction-signal prediction-signal--bullish">{item.risk_reward.toFixed(2)}x</span>
            </div>
            <div className="workflow-levels">
              <div><span>Entry</span><strong>{formatNumber(item.entry_zone[0])} - {formatNumber(item.entry_zone[1])}</strong></div>
              <div><span>Target</span><strong>{formatNumber(item.target_1)}</strong></div>
              <div><span>Stop</span><strong>{formatNumber(item.stop_loss)}</strong></div>
              <div><span>RS vs IHSG</span><strong>{formatPercent(item.relative_strength)}</strong></div>
            </div>
            <div className="workflow-reasons">
              <h3>Alasan</h3>
              <ul>{item.reasons.slice(0, 3).map((reason) => <li key={reason}>{reason}</li>)}</ul>
            </div>
          </article>
        ))
      ) : (
        <div className="api-empty">Belum ada saham yang lolos filter.</div>
      )}
    </section>
  );
}

export default function BacktestPage() {
  const [ticker, setTicker] = useState("BBCA");
  const [startDate, setStartDate] = useState("2024-01-01");
  const [endDate, setEndDate] = useState(new Date().toISOString().slice(0, 10));
  const [horizon, setHorizon] = useState("5d");
  const [ruleEntry, setRuleEntry] = useState("score_gt_70");
  const [backtest, setBacktest] = useState<BacktestResponse | null>(null);
  const [screener, setScreener] = useState<ScreenerResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function runBacktest(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
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
    try {
      const response = await fetch(`${API_BASE_URL}/api/run-idx-screener`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          horizon: horizon === "1d" ? "daily" : horizon === "20d" ? "monthly" : "weekly",
          min_volume: 1000000,
          min_value: 5000000000,
          top_n: 20,
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

  return (
    <div className="dashboard-shell">
      <Sidebar />
      <main className="dashboard-main">
        <div className="dashboard-header">
          <div>
            <p className="dashboard-eyebrow">IDX Research</p>
            <h1>Backtest & Screener</h1>
            <p className="page-subtitle">Uji rule sebelum ranking saham. Ranking hanya dipakai setelah likuiditas, trend, relative strength, bandarmology, dan risk/reward lolos.</p>
          </div>
          <button type="button" onClick={runScreener} disabled={loading}>{loading ? "Memproses" : "Run Screener"}</button>
        </div>

        <form className="watchlist-form workflow-form" onSubmit={runBacktest}>
          <input value={ticker} onChange={(event) => setTicker(event.target.value)} placeholder="BBCA" />
          <input type="date" value={startDate} onChange={(event) => setStartDate(event.target.value)} />
          <input type="date" value={endDate} onChange={(event) => setEndDate(event.target.value)} />
          <select value={horizon} onChange={(event) => setHorizon(event.target.value)}>
            <option value="1d">1d</option>
            <option value="5d">5d</option>
            <option value="20d">20d</option>
          </select>
          <select value={ruleEntry} onChange={(event) => setRuleEntry(event.target.value)}>
            <option value="score_gt_70">Score &gt; 70</option>
            <option value="score_gt_80">Score &gt; 80</option>
            <option value="ma20_gt_ma50">MA20 &gt; MA50</option>
            <option value="breakout">Near Breakout</option>
          </select>
          <button type="submit" disabled={loading}>{loading ? "Memproses" : "Run Backtest"}</button>
        </form>

        {error ? <div className="dashboard-alert">{error}</div> : null}

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
                {backtest.benchmark.beats_benchmark === null ? "No IHSG" : backtest.benchmark.beats_benchmark ? "Beat IHSG" : "Below IHSG"}
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

        {screener ? (
          <>
            <section className="workflow-summary">
              <div className="metric-card"><span>Universe</span><strong>{screener.universe_size}</strong></div>
              <div className="metric-card"><span>Lolos Scan</span><strong>{screener.scanned_size}</strong></div>
              <div className="metric-card"><span>Horizon</span><strong>{screener.horizon}</strong></div>
            </section>
            <ScreenerList title="Top 10 Harian" items={screener.top_daily.slice(0, 10)} />
            <ScreenerList title="Top 10 Mingguan" items={screener.top_weekly.slice(0, 10)} />
            <ScreenerList title="Top 10 Bulanan" items={screener.top_monthly.slice(0, 10)} />
            <ScreenerList title="Avoid / High Risk List" items={screener.avoid_high_risk.slice(0, 10)} />
          </>
        ) : null}
      </main>
    </div>
  );
}
