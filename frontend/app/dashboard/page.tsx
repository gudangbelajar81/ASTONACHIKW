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

type ScannerResponse = {
  top_combinations: ScannerResult[];
};

type TurningPointsResponse = {
  turning_points: TurningPoint[];
  total_detected: number;
};

type DashboardData = {
  composite: CompositePoint[];
  scanner: ScannerResult[];
  turningPoints: TurningPoint[];
  analysis: AnalystSummary | null;
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

      const [compositeResult, scannerResult, turningPointsResult] = await Promise.allSettled([
        compositePromise,
        scannerPromise,
        turningPointsPromise,
      ]);

      if (compositeResult.status === "rejected") {
        throw compositeResult.reason;
      }

      const composite = compositeResult.value;
      const scanner = scannerResult.status === "fulfilled" ? scannerResult.value.top_combinations : [];
      const turningPoints = turningPointsResult.status === "fulfilled" ? turningPointsResult.value.turning_points : [];

      setDataMode("live");
      setData({ composite, scanner, turningPoints, analysis: null });
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
          }),
        });

        setData({ composite, scanner, turningPoints, analysis });
      } catch (analystError) {
        setAnalysisError(analystError instanceof Error ? analystError.message : "AI analysis unavailable");
      }
    } catch (dashboardError) {
      const composite = buildDemoComposite(nextTicker);
      const scanner = buildDemoScanner(nextTicker);
      const turningPoints = buildDemoTurningPoints();

      setLoading(false);
      setDataMode("demo");
      setError(
        dashboardError instanceof Error
          ? `Backend belum aktif, memakai data demo lokal. Detail: ${dashboardError.message}`
          : "Backend belum aktif, memakai data demo lokal."
      );
      setData({ composite, scanner, turningPoints, analysis: buildDemoAnalysis(nextTicker) });
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
            <p className="dashboard-eyebrow">Dashboard</p>
            <h1>Market Cycle Summary</h1>
            <span className={`mode-pill mode-pill--${dataMode}`}>
              {dataMode === "live" ? "Live API" : "Demo Local"}
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
              {loading ? "Loading" : "Refresh"}
            </button>
          </form>
        </div>

        {error ? <div className="dashboard-alert">{error}</div> : null}

        <div className="dashboard-content">
          <section className="cycle-workspace">
            <div className="metric-row">
              <div className="metric-card">
                <span>Latest Cycle</span>
                <strong>{latestPoint ? latestPoint.value.toFixed(3) : "--"}</strong>
              </div>
              <div className="metric-card">
                <span>Projection</span>
                <strong>{projectedCount ? `${projectedCount} days` : "--"}</strong>
              </div>
              <div className="metric-card">
                <span>Signals</span>
                <strong>{data.scanner.length || "--"}</strong>
              </div>
            </div>

            <div className="chart-panel">
              <div className="chart-panel__topline">
                <div>
                  <h2>{ticker} Composite Cycle</h2>
                  <p>Default Venus-Jupiter, Moon-Saturn, and Mercury-Mars blend</p>
                </div>
                <span>{chartData.length} points</span>
              </div>
              <div ref={chartContainerRef} className="chart-card" />
            </div>

            <div className="insight-grid">
              <section className="insight-card">
                <h3>Top Cycle Signals</h3>
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
                  <p>No scanner results yet.</p>
                )}
              </section>

              <section className="insight-card">
                <h3>Next Turning Points</h3>
                <p>
                  Major Top: <strong>{nextTop?.date ?? "Not detected"}</strong>
                </p>
                <p>
                  Major Bottom: <strong>{nextBottom?.date ?? "Not detected"}</strong>
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
