"use client";

import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ColorType, createChart, CrosshairMode, ISeriesApi, LineData, Time } from "lightweight-charts";
import Sidebar from "../../components/Sidebar";
import AIInfoPanel, { AnalystSummary } from "../../components/AIInfoPanel";
import {
  buildDemoAnalysis,
  buildDemoComposite,
  buildDemoScanner,
  buildDemoTurningPoints,
  CompositePoint,
  ScannerResult,
  TurningPoint,
} from "../../lib/demoData";
import { buildAiRequestConfig, readApiProviders } from "../../lib/apiKeys";

type ScannerResponse = {
  top_combinations: ScannerResult[];
};

type TurningPointsResponse = {
  turning_points: TurningPoint[];
  total_detected: number;
};

type PredictionFactor = {
  name: string;
  value: number;
  weight: number;
  contribution: number;
  description: string;
};

type PredictionResponse = {
  ticker: string;
  as_of_date: string;
  horizon_days: number;
  signal: string;
  probability_up: number;
  confidence: string;
  expected_return: number;
  risk_label: string;
  factors: PredictionFactor[];
  backtest: {
    sample_count: number;
    hit_rate: number;
    average_forward_return: number;
    average_signal_return: number;
    max_drawdown: number;
  };
};

type DashboardData = {
  composite: CompositePoint[];
  scanner: ScannerResult[];
  turningPoints: TurningPoint[];
  analysis: AnalystSummary | null;
  prediction: PredictionResponse | null;
};

function getApiBaseUrl() {
  const configuredUrl = process.env.NEXT_PUBLIC_BACKEND_URL ?? process.env.NEXT_PUBLIC_API_URL;
  if (configuredUrl) return configuredUrl;
  if (typeof window !== "undefined" && window.location.hostname.endsWith(".up.railway.app")) {
    return "https://astonachikw-production.up.railway.app";
  }
  return "http://127.0.0.1:8000";
}

const API_BASE_URL = getApiBaseUrl();

const defaultCombinations = [
  { planet_a: "Venus", planet_b: "Jupiter", weight: 1 },
  { planet_a: "Moon", planet_b: "Saturn", weight: 1 },
  { planet_a: "Mercury", planet_b: "Mars", weight: 0.8 },
];

function formatDate(date: Date) {
  return date.toISOString().slice(0, 10);
}

function formatPercent(value: number) {
  return `${(value * 100).toFixed(1)}%`;
}

function buildRange() {
  const end = new Date();
  const start = new Date(end);
  start.setDate(start.getDate() - 180);

  return {
    startDate: formatDate(start),
    endDate: formatDate(end),
  };
}

async function readJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init);

  if (!response.ok) {
    let message = `${response.status} ${response.statusText}`;
    try {
      const body = await response.json();
      message = body.detail ?? message;
    } catch {
      // Keep the HTTP status message when the response is not JSON.
    }
    throw new Error(message);
  }

  return response.json() as Promise<T>;
}

export default function DashboardPage() {
  const [tickerInput, setTickerInput] = useState("AAPL");
  const [ticker, setTicker] = useState("AAPL");
  const [data, setData] = useState<DashboardData>({
    composite: [],
    scanner: [],
    turningPoints: [],
    analysis: null,
    prediction: null,
  });
  const [loading, setLoading] = useState(true);
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [dataMode, setDataMode] = useState<"live" | "demo">("demo");
  const chartContainerRef = useRef<HTMLDivElement | null>(null);
  const seriesRef = useRef<ISeriesApi<"Line"> | null>(null);

  const chartData = useMemo<LineData[]>(() => {
    return data.composite.map((point) => ({
      time: point.date as Time,
      value: Number((point.smoothed_7d ?? point.value).toFixed(4)),
    }));
  }, [data.composite]);

  const projectedCount = useMemo(() => data.composite.filter((point) => point.projected).length, [data.composite]);
  const latestPoint =
    [...data.composite].reverse().find((point) => !point.projected) ?? data.composite.at(-1);
  const nextTop = data.turningPoints.find((point) => point.type === "TOP");
  const nextBottom = data.turningPoints.find((point) => point.type === "BOTTOM");

  const loadDashboard = useCallback(async (nextTicker: string) => {
    setLoading(true);
    setAnalysisLoading(true);
    setError(null);
    setAnalysisError(null);

    const { startDate, endDate } = buildRange();

    try {
      const compositePromise = readJson<CompositePoint[]>(`${API_BASE_URL}/api/composite`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          combinations: defaultCombinations,
          start_date: startDate,
          end_date: endDate,
          smoothing_windows: [7, 30, 60],
          project_days: 30,
        }),
      });

      const scannerPromise = readJson<ScannerResponse>(
        `${API_BASE_URL}/api/scanner?ticker=${encodeURIComponent(nextTicker)}&lookback_years=3`
      );

      const turningPointsPromise = readJson<TurningPointsResponse>(
        `${API_BASE_URL}/api/turning-points?ticker=${encodeURIComponent(nextTicker)}&lookback_days=180`
      );
      const predictionPromise = readJson<PredictionResponse>(
        `${API_BASE_URL}/api/predictions/${encodeURIComponent(nextTicker)}?horizon_days=30`
      );

      const [compositeResult, scannerResult, turningPointsResult, predictionResult] = await Promise.allSettled([
        compositePromise,
        scannerPromise,
        turningPointsPromise,
        predictionPromise,
      ]);

      if (compositeResult.status === "rejected") {
        throw compositeResult.reason;
      }

      const composite = compositeResult.value;
      const scanner = scannerResult.status === "fulfilled" ? scannerResult.value.top_combinations : [];
      const turningPoints = turningPointsResult.status === "fulfilled" ? turningPointsResult.value.turning_points : [];
      const prediction = predictionResult.status === "fulfilled" ? predictionResult.value : null;

      setDataMode("live");
      setData({ composite, scanner, turningPoints, prediction, analysis: null });
      setLoading(false);

      try {
        const analysis = await readJson<AnalystSummary>(`${API_BASE_URL}/api/analyst`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            ticker: nextTicker,
            composite_cycle_data: composite
              .filter((point) => !point.projected)
              .slice(-45)
              .map((point) => ({ date: point.date, value: point.smoothed_7d ?? point.value })),
            turning_points: turningPoints.slice(0, 8),
            scanner_results: scanner.slice(0, 5).map((result) => ({
              cycle: result.cycle,
              correlation: result.correlation,
              lag_days: result.lag_days,
              accuracy: result.accuracy,
              score: result.score,
            })),
            ...buildAiRequestConfig(readApiProviders()),
          }),
        });

        setData({ composite, scanner, turningPoints, prediction, analysis });
      } catch (analystError) {
        setAnalysisError(analystError instanceof Error ? analystError.message : "Analisis AI belum tersedia");
      }
    } catch (dashboardError) {
      const composite = buildDemoComposite(nextTicker);
      const scanner = buildDemoScanner(nextTicker);
      const turningPoints = buildDemoTurningPoints();

      setLoading(false);
      setDataMode("demo");
      setError(
        dashboardError instanceof Error
          ? `Data live belum tersedia, memakai data demo lokal. Detail: ${dashboardError.message}`
          : "Data live belum tersedia, memakai data demo lokal."
      );
      setData({ composite, scanner, turningPoints, prediction: null, analysis: buildDemoAnalysis(nextTicker) });
    } finally {
      setAnalysisLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadDashboard(ticker);
  }, [loadDashboard, ticker]);

  useEffect(() => {
    if (!chartContainerRef.current) return;

    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: 420,
      layout: { background: { type: ColorType.Solid, color: "#071124" }, textColor: "#e2e8f0" },
      grid: {
        vertLines: { color: "rgba(148, 163, 184, 0.08)" },
        horzLines: { color: "rgba(148, 163, 184, 0.08)" },
      },
      crosshair: { mode: CrosshairMode.Normal },
      rightPriceScale: { borderColor: "rgba(148, 163, 184, 0.16)" },
      timeScale: { borderColor: "rgba(148, 163, 184, 0.16)" },
    });

    const lineSeries = chart.addLineSeries({ color: "#38bdf8", lineWidth: 2 });
    seriesRef.current = lineSeries;

    const handleResize = () => chart.applyOptions({ width: chartContainerRef.current?.clientWidth ?? 600 });
    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      chart.remove();
    };
  }, []);

  useEffect(() => {
    seriesRef.current?.setData(chartData);
  }, [chartData]);

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
            <p className="dashboard-eyebrow">Dasbor</p>
            <h1>Ringkasan Siklus Pasar</h1>
            <span className={`mode-pill mode-pill--${dataMode}`}>
              {dataMode === "live" ? "Data Live" : "Demo Lokal"}
            </span>
          </div>

          <form className="ticker-form" onSubmit={handleSubmit}>
            <input
              aria-label="Ticker"
              value={tickerInput}
              onChange={(event) => setTickerInput(event.target.value)}
              placeholder="AAPL"
            />
            <button type="submit" disabled={loading || analysisLoading}>
              {loading ? "Memuat" : "Perbarui"}
            </button>
          </form>
        </div>

        {error ? <div className="dashboard-alert">{error}</div> : null}

        <div className="dashboard-content">
          <section className="cycle-workspace">
            <div className="metric-row">
              <div className="metric-card">
                <span>Siklus Terbaru</span>
                <strong>{latestPoint ? latestPoint.value.toFixed(3) : "--"}</strong>
              </div>
              <div className="metric-card">
                <span>Proyeksi</span>
                <strong>{projectedCount ? `${projectedCount} hari` : "--"}</strong>
              </div>
              <div className="metric-card">
                <span>Sinyal</span>
                <strong>{data.scanner.length || "--"}</strong>
              </div>
            </div>

            <section className="prediction-panel">
              <div className="prediction-panel__header">
                <div>
                  <h2>Skor Prediksi</h2>
                  <p>
                    Horizon {data.prediction?.horizon_days ?? 30} hari
                    {data.prediction ? `, data per ${data.prediction.as_of_date}` : ""}
                  </p>
                </div>
                <span className={`prediction-signal prediction-signal--${data.prediction?.signal ?? "netral"}`}>
                  {data.prediction?.signal ?? "belum tersedia"}
                </span>
              </div>

              {data.prediction ? (
                <>
                  <div className="prediction-metrics">
                    <div>
                      <span>Probabilitas Naik</span>
                      <strong>{formatPercent(data.prediction.probability_up)}</strong>
                    </div>
                    <div>
                      <span>Estimasi Return</span>
                      <strong>{formatPercent(data.prediction.expected_return)}</strong>
                    </div>
                    <div>
                      <span>Confidence</span>
                      <strong>{data.prediction.confidence}</strong>
                    </div>
                    <div>
                      <span>Risiko</span>
                      <strong>{data.prediction.risk_label}</strong>
                    </div>
                  </div>

                  <div className="prediction-backtest">
                    <span>Backtest</span>
                    <strong>{formatPercent(data.prediction.backtest.hit_rate)} hit rate</strong>
                    <span>{data.prediction.backtest.sample_count} sampel historis</span>
                  </div>

                  <div className="prediction-factors">
                    {data.prediction.factors.map((factor) => (
                      <div key={factor.name}>
                        <span>{factor.name}</span>
                        <strong>{factor.contribution.toFixed(3)}</strong>
                      </div>
                    ))}
                  </div>
                </>
              ) : (
                <p className="prediction-empty">Prediksi belum tersedia. Data harga atau provider market mungkin sedang kosong.</p>
              )}
            </section>

            <div className="chart-panel">
              <div className="chart-panel__topline">
                <div>
                  <h2>Siklus Komposit {ticker}</h2>
                  <p>Gabungan default Venus-Jupiter, Moon-Saturn, dan Mercury-Mars</p>
                </div>
                <span>{chartData.length} titik</span>
              </div>
              <div ref={chartContainerRef} className="chart-card" />
            </div>

            <div className="insight-grid">
              <section className="insight-card">
                <h3>Sinyal Siklus Teratas</h3>
                {data.scanner.length ? (
                  <ul>
                    {data.scanner.slice(0, 5).map((signal) => (
                      <li key={signal.cycle}>
                        <span>{signal.cycle}</span>
                        <strong>{Math.round(signal.score * 100)}%</strong>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p>Belum ada hasil scanner.</p>
                )}
              </section>

              <section className="insight-card">
                <h3>Titik Balik Berikutnya</h3>
                <p>
                  Puncak Utama: <strong>{nextTop?.date ?? "Belum terdeteksi"}</strong>
                </p>
                <p>
                  Dasar Utama: <strong>{nextBottom?.date ?? "Belum terdeteksi"}</strong>
                </p>
              </section>
            </div>
          </section>

          <AIInfoPanel analysis={data.analysis} loading={analysisLoading} error={analysisError} ticker={ticker} />
        </div>
      </main>
    </div>
  );
}
