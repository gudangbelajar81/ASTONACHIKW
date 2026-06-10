"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Sidebar from "../../components/Sidebar";
import { useTicker } from "../../context/TickerContext";
import { getApiBaseUrl } from "../../lib/apiBase";
import { readMarketProviders } from "../../lib/apiKeys";

const API_BASE_URL = getApiBaseUrl();

/* ── Types ────────────────────────────────────────────────────────────────── */
type TFSlice = {
  label: string;
  dsi: number;
  dist: number;
  tp: number;
  sl: number;
};

type RadarRow = {
  symbol: string;
  signal: string;
  signal_color: "green" | "blue" | "yellow";
  confluence_score: number;
  dist: number;
  tp: number;
  sl: number;
  last_price: number;
  timeframes: TFSlice[];
  error?: string | null;
};

type RadarResponse = {
  ticker_count: number;
  haka_count: number;
  imbal_count: number;
  pantu_count: number;
  avg_confluence: number;
  timeframe_labels: string[];
  rows: RadarRow[];
  note: string;
};

/* ── Helpers ──────────────────────────────────────────────────────────────── */
function dsiColor(v: number): string {
  if (v >= 65) return "var(--dsi-high)";
  if (v >= 45) return "var(--dsi-mid)";
  return "var(--dsi-low)";
}

function signalClass(color: string): string {
  if (color === "green") return "radar-sig radar-sig--haka";
  if (color === "blue")  return "radar-sig radar-sig--imbal";
  return "radar-sig radar-sig--pantu";
}

function fmtNum(v: number): string {
  if (!v) return "--";
  return new Intl.NumberFormat("id-ID", { maximumFractionDigits: 0 }).format(v);
}

function fmtDist(v: number): string {
  const sign = v >= 0 ? "+" : "";
  return `${sign}${v.toFixed(1)}%`;
}

/* ── Default ticker list (30 saham IDX populer) ──────────────────────────── */
const DEFAULT_TICKERS = [
  "BBCA","BBRI","BMRI","TLKM","ASII","BBNI","BRIS","GOTO","ANTM","MDKA",
  "ADRO","PTBA","ITMG","UNVR","ICBP","INDF","CPIN","KLBF","SMGR","UNTR",
  "EXCL","ISAT","TOWR","MEDC","AKRA","ACES","MAPI","INKP","PGAS","BSDE",
];

/* ── Komponen Baris Radar ─────────────────────────────────────────────────── */
function RadarTableRow({
  row,
  tfLabels,
  onClickTicker,
}: {
  row: RadarRow;
  tfLabels: string[];
  onClickTicker: (t: string) => void;
}) {
  const [expanded, setExpanded] = useState(false);

  return (
    <>
      <tr
        className={`radar-row ${row.signal_color === "green" ? "radar-row--haka" : ""}`}
        onClick={() => setExpanded((p) => !p)}
        title="Klik untuk detail • Klik nama untuk buka Dashboard"
      >
        {/* Ticker */}
        <td>
          <button
            className="radar-ticker-btn"
            onClick={(e) => { e.stopPropagation(); onClickTicker(row.symbol); }}
          >
            {row.symbol}
          </button>
        </td>

        {/* Signal */}
        <td>
          <span className={signalClass(row.signal_color)}>
            {row.signal}
          </span>
        </td>

        {/* DSI per TF */}
        {tfLabels.map((lbl, i) => {
          const tf = row.timeframes[i];
          return (
            <td key={lbl} style={{ color: tf ? dsiColor(tf.dsi) : "var(--ag-text-muted)", fontFamily: "JetBrains Mono, monospace", fontSize: "0.82rem" }}>
              {tf ? `${tf.dsi.toFixed(0)}%` : "--"}
            </td>
          );
        })}

        {/* Confluence */}
        <td style={{ color: dsiColor(row.confluence_score), fontWeight: 700 }}>
          {row.confluence_score.toFixed(0)}%
        </td>

        {/* DIST */}
        <td style={{ color: row.dist >= 0 ? "var(--dsi-high)" : row.dist < -3 ? "#38bdf8" : "var(--dsi-low)" }}>
          {fmtDist(row.dist)}
        </td>

        {/* TP */}
        <td style={{ color: "#38bdf8" }}>{fmtNum(row.tp)}</td>

        {/* SL */}
        <td style={{ color: "#fb923c" }}>{fmtNum(row.sl)}</td>
      </tr>

      {/* Expanded detail row */}
      {expanded && (
        <tr className="radar-expand-row">
          <td colSpan={tfLabels.length + 5}>
            <div className="radar-expand-grid">
              {row.timeframes.map((tf) => (
                <div key={tf.label} className="radar-expand-card">
                  <span className="radar-expand-card__tf">{tf.label}</span>
                  <div className="radar-expand-card__bar">
                    <div
                      className="radar-expand-card__fill"
                      style={{
                        width: `${tf.dsi}%`,
                        background: tf.dsi >= 65 ? "var(--dsi-high)" : tf.dsi >= 45 ? "var(--dsi-mid)" : "var(--dsi-low)",
                      }}
                    />
                  </div>
                  <span style={{ color: dsiColor(tf.dsi), fontWeight: 600 }}>{tf.dsi.toFixed(1)}%</span>
                  <span style={{ color: "var(--ag-text-muted)", fontSize: "0.75rem" }}>
                    DIST {fmtDist(tf.dist)}
                  </span>
                </div>
              ))}
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

/* ── Halaman Utama ────────────────────────────────────────────────────────── */
export default function DSIRadarPage() {
  const { setGlobalTicker } = useTicker();
  const [radar, setRadar] = useState<RadarResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [tickerInput, setTickerInput] = useState(DEFAULT_TICKERS.join(", "));
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [lastUpdate, setLastUpdate] = useState("");
  const [filterSignal, setFilterSignal] = useState<"all" | "haka" | "imbal" | "pantu">("all");
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchRadar = useCallback(async (tickerList: string[]) => {
    setLoading(true);
    setError("");
    try {
      const providers = readMarketProviders();
      const eodhdProvider = providers.find((p) => p.id === "eodhd_intraday");
      const eodhdKey = eodhdProvider?.enabled ? eodhdProvider.apiKey : "";

      const response = await fetch(`${API_BASE_URL}/api/dsi-radar`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          tickers: tickerList, 
          market: "id",
          eodhd_api_key: eodhdKey 
        }),
      });
      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(body?.detail ?? "Gagal mengambil data DSI Radar.");
      }
      const data = (await response.json()) as RadarResponse;
      setRadar(data);
      setLastUpdate(new Date().toLocaleTimeString("id-ID"));
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Error tidak diketahui.");
    } finally {
      setLoading(false);
    }
  }, []);

  function parseTickers(): string[] {
    return tickerInput
      .split(/[\s,;]+/)
      .map((t) => t.trim().toUpperCase())
      .filter(Boolean);
  }

  function handleRun() {
    const tickers = parseTickers();
    if (tickers.length === 0) return;
    void fetchRadar(tickers);
  }

  function handleTickerClick(symbol: string) {
    setGlobalTicker(symbol);
    window.location.href = "/dashboard";
  }

  // Auto-refresh tiap 60 detik
  useEffect(() => {
    if (autoRefresh) {
      intervalRef.current = setInterval(() => {
        void fetchRadar(parseTickers());
      }, 60_000);
    } else {
      if (intervalRef.current) clearInterval(intervalRef.current);
    }
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoRefresh, tickerInput]);

  // Filter rows
  const filteredRows = radar?.rows.filter((r) => {
    if (filterSignal === "all") return true;
    if (filterSignal === "haka") return r.signal_color === "green";
    if (filterSignal === "imbal") return r.signal_color === "blue";
    return r.signal_color === "yellow";
  }) ?? [];

  const tfLabels = radar?.timeframe_labels ?? ["1m","5m","15m","30m","1h","4h","D"];

  return (
    <div className="dashboard-shell">
      <Sidebar />
      <main className="dashboard-main radar-main">
        {/* ── Header ── */}
        <div className="dashboard-header">
          <div>
            <p className="dashboard-eyebrow">DSI Command Center</p>
            <h1>🎯 Multi-TF Radar</h1>
            <p className="page-subtitle">
              Demand Supply Index × 7 Timeframe untuk banyak saham sekaligus.
              {lastUpdate && <span className="radar-update-badge">Update: {lastUpdate}</span>}
            </p>
          </div>
          <div className="radar-controls">
            <label className="radar-autorefresh">
              <input
                type="checkbox"
                checked={autoRefresh}
                onChange={(e) => setAutoRefresh(e.target.checked)}
              />
              <span>Auto-refresh 60s</span>
            </label>
            <button className="action-button" onClick={handleRun} disabled={loading}>
              {loading ? "⏳ Memuat..." : "🔍 Scan"}
            </button>
          </div>
        </div>

        {/* ── Input Ticker ── */}
        <section className="radar-input-section">
          <label className="radar-input-label">Daftar Saham (pisah koma / spasi, maks 50):</label>
          <div className="radar-input-row">
            <textarea
              className="radar-ticker-input"
              value={tickerInput}
              onChange={(e) => setTickerInput(e.target.value)}
              rows={2}
              placeholder="BBCA, TLKM, GOTO, ANTM, ..."
            />
            <div className="radar-preset-btns">
              <button className="sort-btn" onClick={() => setTickerInput(DEFAULT_TICKERS.join(", "))}>
                IDX 30
              </button>
              <button className="sort-btn" onClick={() => setTickerInput(
                "BBCA,BBRI,BMRI,BBNI,BRIS,BTPS,BBTN,MEGA,BDMN,NISP"
              )}>
                Perbankan
              </button>
              <button className="sort-btn" onClick={() => setTickerInput(
                "ADRO,PTBA,ITMG,ANTM,MDKA,INCO,BUMI,HRUM,PGAS,MEDC"
              )}>
                Tambang
              </button>
              <button className="sort-btn" onClick={() => setTickerInput(
                "TLKM,EXCL,ISAT,TOWR,GOTO,MTEL,EMTK"
              )}>
                Teknologi
              </button>
            </div>
          </div>
        </section>

        {error && <div className="dashboard-alert">{error}</div>}

        {/* ── Summary Bar ── */}
        {radar && (
          <section className="radar-summary-bar">
            <div className="radar-summary-item radar-summary-item--haka">
              <span>🟢 HAKA</span>
              <strong>{radar.haka_count}</strong>
            </div>
            <div className="radar-summary-item radar-summary-item--imbal">
              <span>🔵 IMBAL</span>
              <strong>{radar.imbal_count}</strong>
            </div>
            <div className="radar-summary-item radar-summary-item--pantu">
              <span>⚪ PANTU</span>
              <strong>{radar.pantu_count}</strong>
            </div>
            <div className="radar-summary-item">
              <span>Confluence</span>
              <strong style={{ color: dsiColor(radar.avg_confluence) }}>
                {radar.avg_confluence.toFixed(0)}%
              </strong>
            </div>
            <div className="radar-summary-item">
              <span>Total</span>
              <strong>{radar.ticker_count}</strong>
            </div>
          </section>
        )}

        {/* ── Filter Signal ── */}
        {radar && (
          <div className="screener-controls" style={{ marginBottom: "1rem" }}>
            <div className="screener-controls__group">
              <label>Filter Signal:</label>
              <div className="sort-buttons">
                {([
                  ["all",   "Semua"],
                  ["haka",  "🟢 HAKA"],
                  ["imbal", "🔵 IMBAL"],
                  ["pantu", "⚪ PANTU"],
                ] as [string, string][]).map(([val, label]) => (
                  <button
                    key={val}
                    type="button"
                    className={filterSignal === val ? "sort-btn active" : "sort-btn"}
                    onClick={() => setFilterSignal(val as typeof filterSignal)}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* ── Radar Table ── */}
        {radar ? (
          <div className="radar-table-wrap">
            <table className="radar-table">
              <thead>
                <tr>
                  <th>TICKER</th>
                  <th>SIGNAL</th>
                  {tfLabels.map((lbl) => <th key={lbl}>{lbl}</th>)}
                  <th title="Confluence Score: rata-rata tertimbang semua TF">CONF</th>
                  <th title="Jarak harga vs VWAP">DIST</th>
                  <th>TP</th>
                  <th>SL</th>
                </tr>
              </thead>
              <tbody>
                {filteredRows.length === 0 ? (
                  <tr>
                    <td colSpan={tfLabels.length + 5} className="radar-empty">
                      Tidak ada saham yang cocok dengan filter ini.
                    </td>
                  </tr>
                ) : (
                  filteredRows.map((row) => (
                    <RadarTableRow
                      key={row.symbol}
                      row={row}
                      tfLabels={tfLabels}
                      onClickTicker={handleTickerClick}
                    />
                  ))
                )}
              </tbody>
            </table>
          </div>
        ) : !loading ? (
          <div className="api-empty" style={{ marginTop: "2rem" }}>
            <p>🎯 Klik tombol <strong>Scan</strong> untuk memulai analisis DSI multi-timeframe.</p>
            <p style={{ marginTop: "0.5rem", fontSize: "0.85rem", color: "var(--ag-text-muted)" }}>
              Klik nama saham di tabel untuk membuka analisis lengkap di Dasbor.
            </p>
          </div>
        ) : null}

        {radar && (
          <p className="screener-note" style={{ marginTop: "1rem" }}>{radar.note}</p>
        )}
      </main>
    </div>
  );
}
