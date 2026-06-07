"use client";

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { ColorType, createChart, ISeriesApi, Time } from "lightweight-charts";
import Sidebar from "../../components/Sidebar";
import { buildMarketProviderConfig, readMarketProviders } from "../../lib/apiKeys";
import { appendUsageEvent, normalizeTickerForMarket, readMarketMode } from "../../lib/userData";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "https://astonachikw-production.up.railway.app";

type OHLCVPoint = {
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
  source?: string;
  provider_name?: string | null;
  provider_status?: string | null;
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
  points: OHLCVPoint[];
  bandarmology: Bandarmology;
  market_data_provider?: string | null;
};

function formatPercent(value: number) {
  return `${(value * 100).toFixed(1)}%`;
}

export default function OHLCVPage() {
  const [tickerInput, setTickerInput] = useState("AAPL");
  const [ticker, setTicker] = useState("AAPL");
  const [report, setReport] = useState<OHLCVReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const chartRef = useRef<HTMLDivElement | null>(null);
  const volumeRef = useRef<HTMLDivElement | null>(null);
  const candleSeriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const ma20Ref = useRef<ISeriesApi<"Line"> | null>(null);
  const ma50Ref = useRef<ISeriesApi<"Line"> | null>(null);
  const ma200Ref = useRef<ISeriesApi<"Line"> | null>(null);
  const volumeSeriesRef = useRef<ISeriesApi<"Histogram"> | null>(null);

  async function loadReport(nextTicker: string) {
    setLoading(true);
    setError("");
    try {
      const marketProviders = readMarketProviders();
      const liveProviders = buildMarketProviderConfig(marketProviders).market_data_providers;
      const useLiveProvider = liveProviders.length > 0;
      const response = await fetch(
        useLiveProvider ? `${API_BASE_URL}/api/ohlcv/live/${encodeURIComponent(nextTicker)}` : `${API_BASE_URL}/api/ohlcv/${encodeURIComponent(nextTicker)}?lookback_days=180`,
        useLiveProvider
          ? {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                ticker: nextTicker,
                lookback_days: 180,
                market_data_providers: liveProviders,
              }),
            }
          : undefined
      );
      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(body?.detail ?? `${response.status} ${response.statusText}`);
      }
      setReport((await response.json()) as OHLCVReport);
      appendUsageEvent({ action: "ohlcv_load", ticker: nextTicker, source: "ohlcv" });
    } catch (exc) {
      setReport(null);
      setError(exc instanceof Error ? exc.message : "Gagal membaca OHLCV.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadReport(ticker);
  }, [ticker]);

  useEffect(() => {
    if (!chartRef.current || !volumeRef.current) return;

    const chart = createChart(chartRef.current, {
      width: chartRef.current.clientWidth,
      height: 460,
      layout: { background: { type: ColorType.Solid, color: "#071124" }, textColor: "#e2e8f0" },
      grid: {
        vertLines: { color: "rgba(148, 163, 184, 0.08)" },
        horzLines: { color: "rgba(148, 163, 184, 0.08)" },
      },
      rightPriceScale: { borderColor: "rgba(148, 163, 184, 0.16)" },
      timeScale: { borderColor: "rgba(148, 163, 184, 0.16)" },
    });
    const volumeChart = createChart(volumeRef.current, {
      width: volumeRef.current.clientWidth,
      height: 130,
      layout: { background: { type: ColorType.Solid, color: "#071124" }, textColor: "#94a3b8" },
      grid: {
        vertLines: { color: "rgba(148, 163, 184, 0.06)" },
        horzLines: { color: "rgba(148, 163, 184, 0.06)" },
      },
    });

    candleSeriesRef.current = chart.addCandlestickSeries({
      upColor: "#22c55e",
      downColor: "#ef4444",
      borderVisible: false,
      wickUpColor: "#22c55e",
      wickDownColor: "#ef4444",
    });
    ma20Ref.current = chart.addLineSeries({ color: "#38bdf8", lineWidth: 2 });
    ma50Ref.current = chart.addLineSeries({ color: "#fbbf24", lineWidth: 2 });
    ma200Ref.current = chart.addLineSeries({ color: "#c084fc", lineWidth: 2 });
    volumeSeriesRef.current = volumeChart.addHistogramSeries({ color: "#38bdf8" });

    const handleResize = () => {
      chart.applyOptions({ width: chartRef.current?.clientWidth ?? 600 });
      volumeChart.applyOptions({ width: volumeRef.current?.clientWidth ?? 600 });
    };
    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      chart.remove();
      volumeChart.remove();
    };
  }, []);

  useEffect(() => {
    if (!report) return;
    candleSeriesRef.current?.setData(
      report.points.map((point) => ({
        time: point.date as Time,
        open: point.open,
        high: point.high,
        low: point.low,
        close: point.close,
      }))
    );
    ma20Ref.current?.setData(report.points.filter((point) => point.ma20).map((point) => ({ time: point.date as Time, value: point.ma20 as number })));
    ma50Ref.current?.setData(report.points.filter((point) => point.ma50).map((point) => ({ time: point.date as Time, value: point.ma50 as number })));
    ma200Ref.current?.setData(report.points.filter((point) => point.ma200).map((point) => ({ time: point.date as Time, value: point.ma200 as number })));
    volumeSeriesRef.current?.setData(
      report.points.map((point) => ({
        time: point.date as Time,
        value: point.volume,
        color: point.close >= point.open ? "rgba(34, 197, 94, 0.55)" : "rgba(239, 68, 68, 0.55)",
      }))
    );
  }, [report]);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalizedTicker = normalizeTickerForMarket(tickerInput, readMarketMode());
    if (normalizedTicker) setTicker(normalizedTicker);
  }

  const latestClose = useMemo(() => report?.points.at(-1)?.close, [report]);
  const liveProviderLabel = useMemo(() => {
    if (!report?.bandarmology) return "";
    if (report.bandarmology.source === "live" && report.bandarmology.provider_name) {
      return `Live: ${report.bandarmology.provider_name}`;
    }
    if (report.bandarmology.source === "internal_fallback" && report.bandarmology.provider_name) {
      return `Fallback: ${report.bandarmology.provider_name}`;
    }
    return report?.market_data_provider ? `Provider: ${report.market_data_provider}` : "Internal proxy";
  }, [report]);

  return (
    <div className="dashboard-shell">
      <Sidebar />
      <main className="dashboard-main">
        <div className="dashboard-header">
          <div>
            <p className="dashboard-eyebrow">OHLCV Pro</p>
            <h1>Chart & Bandarmology Proxy</h1>
          </div>
          <form className="ticker-form" onSubmit={handleSubmit}>
            <input value={tickerInput} onChange={(event) => setTickerInput(event.target.value)} />
            <button type="submit" disabled={loading}>{loading ? "Memuat" : "Cek"}</button>
          </form>
        </div>

        {error ? <div className="dashboard-alert">{error}</div> : null}

        <div className="ohlcv-layout">
          <section className="ohlcv-chart-panel">
            <div className="chart-panel__topline">
              <div>
                <h2>{report?.ticker ?? ticker} Candlestick</h2>
                <p>MA20 biru, MA50 kuning, MA200 ungu. Close terakhir: {latestClose ?? "--"}</p>
              </div>
              <span>{liveProviderLabel}</span>
            </div>
            <div ref={chartRef} className="ohlcv-chart" />
            <div ref={volumeRef} className="ohlcv-volume" />
          </section>

          <aside className="bandar-panel">
            <h2>Bandarmology Proxy</h2>
            {report ? (
              <>
              <span className={`prediction-signal prediction-signal--${report.bandarmology.verdict === "distribusi" ? "bearish" : report.bandarmology.verdict === "akumulasi" ? "bullish" : "netral"}`}>
                {report.bandarmology.verdict}
              </span>
              <p className="page-subtitle">
                {report.bandarmology.source === "live"
                  ? "Bandarmology live dibaca dari provider yang aktif di Settings."
                  : report.bandarmology.source === "internal_fallback"
                    ? "Provider live gagal, app memakai fallback internal."
                    : "Bandarmology proxy internal aktif."}
              </p>
              <div className="bandar-metrics">
                <div><span>Smart Money</span><strong>{formatPercent(report.bandarmology.smart_money_score)}</strong></div>
                <div><span>Akumulasi</span><strong>{formatPercent(report.bandarmology.accumulation_score)}</strong></div>
                <div><span>Distribusi</span><strong>{formatPercent(report.bandarmology.distribution_score)}</strong></div>
                  <div><span>Volume Spike</span><strong>{report.bandarmology.volume_spike.toFixed(2)}x</strong></div>
                  <div><span>OBV</span><strong>{report.bandarmology.obv_trend}</strong></div>
                  <div><span>Money Flow</span><strong>{formatPercent(report.bandarmology.money_flow_score)}</strong></div>
                  <div><span>Support</span><strong>{report.bandarmology.support}</strong></div>
                  <div><span>Resistance</span><strong>{report.bandarmology.resistance}</strong></div>
                </div>
                <ul>
                  {report.bandarmology.notes.map((note) => <li key={note}>{note}</li>)}
                </ul>
              </>
            ) : (
              <p>{loading ? "Mengambil data OHLCV..." : "Belum ada data."}</p>
            )}
          </aside>
        </div>
      </main>
    </div>
  );
}
