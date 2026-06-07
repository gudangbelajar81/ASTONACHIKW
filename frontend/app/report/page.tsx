"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import Sidebar from "../../components/Sidebar";
import { appendReportLog, appendUsageEvent, normalizeTickerForMarket, readMarketMode } from "../../lib/userData";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "https://astonachikw-production.up.railway.app";

type Prediction = {
  ticker: string;
  as_of_date: string;
  horizon_days: number;
  signal: string;
  probability_up: number;
  confidence: string;
  expected_return: number;
  risk_label: string;
  regime: {
    label: string;
    description: string;
    trend_score: number;
    volatility_score: number;
    momentum_score: number;
  };
  sentiment?: { label: string; score: number; description: string; headline_count?: number } | null;
  macro?: { risk_budget: string; beta: number; correlation: number; relative_strength: number; description: string } | null;
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
  factors: { name: string; value: number; weight: number; contribution: number; description: string }[];
  backtest: {
    sample_count: number;
    hit_rate: number;
    average_forward_return: number;
    average_signal_return: number;
    max_drawdown: number;
  };
};

type OhlcvPoint = {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  ma20: number | null;
  ma50: number | null;
  ma200: number | null;
};

type Bandarmology = {
  smart_money_score: number;
  accumulation_score: number;
  distribution_score: number;
  volume_spike: number;
  obv_trend: string;
  money_flow_score: number;
  support: number;
  resistance: number;
  verdict: string;
  notes: string[];
};

type OHLCVReport = {
  ticker: string;
  points: OhlcvPoint[];
  bandarmology: Bandarmology;
};

type PerformanceReport = {
  verdict: string;
  backtest: Prediction["backtest"];
};

type ReportBundle = {
  prediction: Prediction;
  ohlcv: OHLCVReport | null;
  performance: PerformanceReport | null;
  generatedAt: string;
};

function formatPercent(value: number | null | undefined) {
  if (value === null || value === undefined) return "--";
  return `${(value * 100).toFixed(1)}%`;
}

function formatCurrency(value: number | null | undefined) {
  if (value === null || value === undefined) return "--";
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(value);
}

async function fetchJson<T>(url: string): Promise<T> {
  const response = await fetch(url);
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? `${response.status} ${response.statusText}`);
  }
  return response.json() as Promise<T>;
}

export default function ReportPage() {
  const [tickerInput, setTickerInput] = useState("AAPL");
  const [ticker, setTicker] = useState("AAPL");
  const [report, setReport] = useState<ReportBundle | null>(null);
  const [loading, setLoading] = useState(true);
  const [printing, setPrinting] = useState(false);
  const [error, setError] = useState("");

  const latestClose = useMemo(() => report?.ohlcv?.points.at(-1)?.close ?? null, [report]);

  async function loadReport(nextTicker: string) {
    setLoading(true);
    setError("");
    try {
      const [predictionResult, ohlcvResult, performanceResult] = await Promise.allSettled([
        fetchJson<Prediction>(`${API_BASE_URL}/api/predictions/${encodeURIComponent(nextTicker)}?horizon_days=30`),
        fetchJson<OHLCVReport>(`${API_BASE_URL}/api/ohlcv/${encodeURIComponent(nextTicker)}?lookback_days=180`),
        fetchJson<PerformanceReport>(`${API_BASE_URL}/api/performance/${encodeURIComponent(nextTicker)}?horizon_days=30`),
      ]);

      if (predictionResult.status === "rejected") throw predictionResult.reason;

      const nextReport: ReportBundle = {
        prediction: predictionResult.value,
        ohlcv: ohlcvResult.status === "fulfilled" ? ohlcvResult.value : null,
        performance: performanceResult.status === "fulfilled" ? performanceResult.value : null,
        generatedAt: new Date().toISOString(),
      };

      setReport(nextReport);
      appendReportLog({
        ticker: nextTicker,
        signal: nextReport.prediction.signal,
        regime: nextReport.prediction.regime.label,
        confidence: nextReport.prediction.confidence,
      });
      appendUsageEvent({ action: "report_generate", ticker: nextTicker, source: "report" });
    } catch (exc) {
      setReport(null);
      setError(exc instanceof Error ? exc.message : "Gagal membuat report strategi.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadReport(ticker);
  }, [ticker]);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalizedTicker = normalizeTickerForMarket(tickerInput, readMarketMode());
    if (normalizedTicker) setTicker(normalizedTicker);
  }

  function printReport() {
    setPrinting(true);
    window.print();
    window.setTimeout(() => setPrinting(false), 400);
  }

  return (
    <div className="dashboard-shell">
      <Sidebar />
      <main className="dashboard-main">
        <div className="dashboard-header no-print">
          <div>
            <p className="dashboard-eyebrow">Report</p>
            <h1>Strategy Report</h1>
            <p className="page-subtitle">Ringkasan yang bisa dicetak atau disimpan ke PDF dari browser.</p>
          </div>
          <div className="report-toolbar">
            <form className="ticker-form" onSubmit={handleSubmit}>
              <input value={tickerInput} onChange={(event) => setTickerInput(event.target.value)} />
              <button type="submit" disabled={loading}>
                {loading ? "Memuat" : "Generate"}
              </button>
            </form>
            <button className="action-button" type="button" onClick={printReport} disabled={!report || printing}>
              {printing ? "Mencetak..." : "Cetak PDF"}
            </button>
          </div>
        </div>

        {error ? <div className="dashboard-alert no-print">{error}</div> : null}

        {report ? (
          <article className="strategy-report">
            <header className="strategy-report__hero">
              <div>
                <p>{report.prediction.ticker}</p>
                <h2>{report.prediction.signal.toUpperCase()}</h2>
                <span>Generated {new Date(report.generatedAt).toLocaleString("id-ID")}</span>
              </div>
              <div className={`strategy-report__badge strategy-report__badge--${report.prediction.signal}`}>
                {report.prediction.signal}
              </div>
            </header>

            <section className="report-section">
              <h3>Ringkasan</h3>
              <div className="report-card-grid">
                <div><span>Probabilitas Naik</span><strong>{formatPercent(report.prediction.probability_up)}</strong></div>
                <div><span>Estimasi Return</span><strong>{formatPercent(report.prediction.expected_return)}</strong></div>
                <div><span>Confidence</span><strong>{report.prediction.confidence}</strong></div>
                <div><span>Risk Label</span><strong>{report.prediction.risk_label}</strong></div>
                <div><span>Latest Close</span><strong>{formatCurrency(latestClose)}</strong></div>
                <div><span>Horizon</span><strong>{report.prediction.horizon_days} hari</strong></div>
              </div>
            </section>

            <section className="report-section">
              <h3>Regime & Konteks</h3>
              <div className="context-grid">
                <div>
                  <span>Market Regime</span>
                  <strong>{report.prediction.regime.label}</strong>
                  <p>{report.prediction.regime.description}</p>
                </div>
                <div>
                  <span>Sentimen</span>
                  <strong>{report.prediction.sentiment?.label ?? "netral"}</strong>
                  <p>{report.prediction.sentiment?.description ?? "Belum ada headline kuat."}</p>
                </div>
                <div>
                  <span>Macro Risk</span>
                  <strong>{report.prediction.macro?.risk_budget ?? "normal"}</strong>
                  <p>{report.prediction.macro?.description ?? "Konteks makro belum tersedia."}</p>
                </div>
                <div>
                  <span>Bandarmology</span>
                  <strong>{report.ohlcv?.bandarmology.verdict ?? "netral"}</strong>
                  <p>{report.ohlcv ? "Proxy volume dan price action sudah dihitung." : "Data OHLCV belum tersedia."}</p>
                </div>
              </div>
            </section>

            {report.prediction.scenario ? (
              <section className="report-section">
                <h3>Scenario Planner</h3>
                <div className="scenario-panel">
                  <div><span>Entry Low</span><strong>{formatCurrency(report.prediction.scenario.entry_zone_low)}</strong></div>
                  <div><span>Entry High</span><strong>{formatCurrency(report.prediction.scenario.entry_zone_high)}</strong></div>
                  <div><span>Invalidation</span><strong>{formatCurrency(report.prediction.scenario.invalidation_level)}</strong></div>
                  <div><span>Target Bullish</span><strong>{formatCurrency(report.prediction.scenario.bullish_target)}</strong></div>
                  <div><span>Target Bearish</span><strong>{formatCurrency(report.prediction.scenario.bearish_target)}</strong></div>
                  <div><span>Position Size</span><strong>{report.prediction.scenario.position_size_shares} saham</strong></div>
                </div>
                <p className="report-notes">{report.prediction.scenario.playbook}</p>
              </section>
            ) : null}

            <section className="report-section report-two-col">
              <article>
                <h3>Backtest</h3>
                <div className="report-card-grid report-card-grid--compact">
                  <div><span>Hit Rate</span><strong>{formatPercent(report.prediction.backtest.hit_rate)}</strong></div>
                  <div><span>Avg Signal Return</span><strong>{formatPercent(report.prediction.backtest.average_signal_return)}</strong></div>
                  <div><span>Forward Return</span><strong>{formatPercent(report.prediction.backtest.average_forward_return)}</strong></div>
                  <div><span>Max Drawdown</span><strong>{formatPercent(report.prediction.backtest.max_drawdown)}</strong></div>
                </div>
              </article>

              <article>
                <h3>Bandarmology Notes</h3>
                {report.ohlcv ? (
                  <>
                    <div className="report-card-grid report-card-grid--compact">
                      <div><span>Smart Money</span><strong>{formatPercent(report.ohlcv.bandarmology.smart_money_score)}</strong></div>
                      <div><span>Accumulation</span><strong>{formatPercent(report.ohlcv.bandarmology.accumulation_score)}</strong></div>
                      <div><span>Distribution</span><strong>{formatPercent(report.ohlcv.bandarmology.distribution_score)}</strong></div>
                      <div><span>Volume Spike</span><strong>{report.ohlcv.bandarmology.volume_spike.toFixed(2)}x</strong></div>
                    </div>
                    <ul className="report-notes-list">
                      {report.ohlcv.bandarmology.notes.map((note) => (
                        <li key={note}>{note}</li>
                      ))}
                    </ul>
                  </>
                ) : (
                  <p className="report-notes">OHLCV belum berhasil dimuat, jadi bagian ini hanya menampilkan prediksi utama.</p>
                )}
              </article>
            </section>

            {report.performance ? (
              <section className="report-section">
                <h3>Snapshot Performance</h3>
                <div className="report-card-grid">
                  <div><span>Verdict</span><strong>{report.performance.verdict}</strong></div>
                  <div><span>Hit Rate</span><strong>{formatPercent(report.performance.backtest.hit_rate)}</strong></div>
                  <div><span>Sample Count</span><strong>{report.performance.backtest.sample_count}</strong></div>
                  <div><span>Avg Signal Return</span><strong>{formatPercent(report.performance.backtest.average_signal_return)}</strong></div>
                </div>
              </section>
            ) : null}

            <footer className="report-footer">
              <span>AstroCycle Strategy Report</span>
              <span>Disclaimer: laporan ini bersifat informatif dan bukan nasihat investasi.</span>
            </footer>
          </article>
        ) : loading ? (
          <div className="api-empty no-print">Membuat strategy report...</div>
        ) : null}
      </main>
    </div>
  );
}
