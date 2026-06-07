"use client";

import { FormEvent, useEffect, useState } from "react";
import Sidebar from "../../components/Sidebar";
import {
  AlertCondition,
  UserAlert,
  appendUsageEvent,
  makeId,
  normalizeTickerForMarket,
  readAlerts,
  readMarketMode,
  writeAlerts,
} from "../../lib/userData";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "https://astonachikw-production.up.railway.app";

type AlertResult = {
  alert: UserAlert;
  triggered: boolean;
  actual: string;
  message: string;
};

function evaluateAlert(alert: UserAlert, prediction: any): AlertResult {
  const actualMap: Record<AlertCondition, string | number> = {
    probability_up: prediction.probability_up,
    expected_return: prediction.expected_return,
    risk_label: prediction.risk_label,
    regime: prediction.regime?.label ?? "",
  };
  const actual = actualMap[alert.condition];
  const targetNumber = Number(alert.target);
  let triggered = false;

  if (alert.operator === "equals") {
    triggered = String(actual).toLowerCase() === alert.target.toLowerCase();
  } else if (typeof actual === "number" && Number.isFinite(targetNumber)) {
    triggered = alert.operator === ">=" ? actual >= targetNumber : actual <= targetNumber;
  }

  return {
    alert,
    triggered,
    actual: typeof actual === "number" ? `${(actual * 100).toFixed(1)}%` : String(actual),
    message: triggered ? "Kondisi terpenuhi" : "Belum terpenuhi",
  };
}

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<UserAlert[]>([]);
  const [results, setResults] = useState<AlertResult[]>([]);
  const [ticker, setTicker] = useState("AAPL");
  const [condition, setCondition] = useState<AlertCondition>("probability_up");
  const [operator, setOperator] = useState<">=" | "<=" | "equals">(">=");
  const [target, setTarget] = useState("0.65");
  const [checking, setChecking] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    setAlerts(readAlerts());
  }, []);

  function save(nextAlerts: UserAlert[]) {
    setAlerts(nextAlerts);
    writeAlerts(nextAlerts);
  }

  function addAlert(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nextTicker = normalizeTickerForMarket(ticker, readMarketMode());
    save([
      ...alerts,
      {
        id: makeId(),
        ticker: nextTicker,
        condition,
        operator,
        target,
        enabled: true,
      },
    ]);
    appendUsageEvent({ action: "alert_add", ticker: nextTicker, source: "alerts" });
  }

  async function checkAlerts() {
    setChecking(true);
    setError("");
    try {
      const nextResults: AlertResult[] = [];
      for (const alert of alerts.filter((item) => item.enabled)) {
        const response = await fetch(`${API_BASE_URL}/api/predictions/${encodeURIComponent(alert.ticker)}?horizon_days=30`);
        if (!response.ok) continue;
        const prediction = await response.json();
        nextResults.push(evaluateAlert(alert, prediction));
      }
      setResults(nextResults);
      appendUsageEvent({ action: "alert_check", ticker: ticker.trim().toUpperCase(), source: "alerts" });
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Gagal mengecek alert.");
    } finally {
      setChecking(false);
    }
  }

  return (
    <div className="dashboard-shell">
      <Sidebar />
      <main className="dashboard-main">
        <div className="dashboard-header">
          <div>
            <p className="dashboard-eyebrow">Alerts</p>
            <h1>Alert System</h1>
          </div>
          <button className="action-button" type="button" onClick={checkAlerts} disabled={checking || !alerts.length}>
            {checking ? "Mengecek..." : "Cek Alerts"}
          </button>
        </div>

        {error ? <div className="dashboard-alert">{error}</div> : null}

        <form className="alert-form" onSubmit={addAlert}>
          <input value={ticker} onChange={(event) => setTicker(event.target.value)} placeholder="Ticker" />
          <select value={condition} onChange={(event) => setCondition(event.target.value as AlertCondition)}>
            <option value="probability_up">Probabilitas Naik</option>
            <option value="expected_return">Expected Return</option>
            <option value="risk_label">Risk Label</option>
            <option value="regime">Regime</option>
          </select>
          <select value={operator} onChange={(event) => setOperator(event.target.value as any)}>
            <option value=">=">&gt;=</option>
            <option value="<=">&lt;=</option>
            <option value="equals">equals</option>
          </select>
          <input value={target} onChange={(event) => setTarget(event.target.value)} placeholder="0.65 / bullish" />
          <button type="submit">Tambah Alert</button>
        </form>

        <section className="utility-grid">
          <article className="utility-card">
            <h2>Daftar Alert</h2>
            {alerts.length ? (
              alerts.map((alert) => (
                <div className="utility-row" key={alert.id}>
                  <span>{alert.ticker}</span>
                  <strong>{alert.condition} {alert.operator} {alert.target}</strong>
                  <button type="button" onClick={() => save(alerts.filter((item) => item.id !== alert.id))}>Hapus</button>
                </div>
              ))
            ) : (
              <p>Belum ada alert.</p>
            )}
          </article>

          <article className="utility-card">
            <h2>Hasil Cek</h2>
            {results.length ? (
              results.map((result) => (
                <div className={`utility-row utility-row--${result.triggered ? "live" : "dead"}`} key={result.alert.id}>
                  <span>{result.alert.ticker}</span>
                  <strong>{result.message}</strong>
                  <span>Aktual: {result.actual}</span>
                </div>
              ))
            ) : (
              <p>Tekan Cek Alerts untuk melihat status.</p>
            )}
          </article>
        </section>
      </main>
    </div>
  );
}
