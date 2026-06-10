"use client";

import React from "react";

/* ── Types ── */
interface TimeframeAnalysis {
  timeframe: string;
  status: "ok" | "insufficient_data" | "pending_realtime";
  score?: number | null;
  bias?: string | null;
  trend?: string;
  market_structure?: string;
  breakout_status?: string;
  momentum?: string;
  message?: string;
  indicators?: {
    rsi?: number;
    macd_histogram?: number;
    macd_crossing_up?: boolean;
    adx?: number;
    stochastic?: number;
    ma20?: number;
    ma50?: number;
  };
}

interface AlignmentData {
  score: number;
  bias: string;
  label: string;
  bullish_timeframe_count: number;
  trade_ready: boolean;
  trade_readiness_note: string;
}

interface MultiTimeframeData {
  timeframes: Record<string, TimeframeAnalysis>;
  alignment: AlignmentData;
}

interface MultiTimeframePanelProps {
  data: MultiTimeframeData | null;
  loading?: boolean;
}

/* ── Helper Functions ── */
const BIAS_CONFIG: Record<string, { color: string; label: string; emoji: string }> = {
  bullish:           { color: "#6ee7b7", label: "Bullish",         emoji: "↑" },
  neutral_bullish:   { color: "#7dd3fc", label: "Netral Bullish",  emoji: "↗" },
  neutral_bearish:   { color: "#fcd34d", label: "Netral Bearish",  emoji: "↘" },
  bearish:           { color: "#fda4af", label: "Bearish",         emoji: "↓" },
};

const MOMENTUM_CONFIG: Record<string, { color: string; label: string }> = {
  strengthening: { color: "#6ee7b7", label: "Menguat"  },
  positive:      { color: "#7dd3fc", label: "Positif"  },
  mixed:         { color: "#fcd34d", label: "Campuran" },
  weakening:     { color: "#fda4af", label: "Melemah"  },
};

const TF_ORDER = ["monthly", "weekly", "daily", "1h", "15m"];
const TF_LABELS: Record<string, string> = {
  monthly: "Monthly",
  weekly:  "Weekly",
  daily:   "Daily",
  "1h":    "1 Jam",
  "15m":   "15 Menit",
};

function ScorePill({ score }: { score: number }) {
  const color =
    score >= 70 ? "#6ee7b7" :
    score >= 50 ? "#7dd3fc" :
    score >= 35 ? "#fcd34d" : "#fda4af";
  const bg =
    score >= 70 ? "rgba(16,185,129,0.12)" :
    score >= 50 ? "rgba(56,189,248,0.12)" :
    score >= 35 ? "rgba(251,191,36,0.12)" : "rgba(244,63,94,0.12)";

  return (
    <span style={{
      display: "inline-flex",
      alignItems: "center",
      justifyContent: "center",
      minWidth: 38,
      padding: "2px 8px",
      borderRadius: "var(--ag-radius-pill)",
      background: bg,
      color,
      fontSize: "0.78rem",
      fontWeight: 800,
      fontFamily: "'JetBrains Mono', monospace",
      border: `1px solid ${color}40`,
    }}>
      {score}
    </span>
  );
}

function ProgressBar({ value, max = 100 }: { value: number; max?: number }) {
  const pct = Math.min(100, Math.max(0, (value / max) * 100));
  const color =
    pct >= 70 ? "#10b981" :
    pct >= 50 ? "#38bdf8" :
    pct >= 35 ? "#f59e0b" : "#f43f5e";
  return (
    <div style={{
      width: "100%",
      height: 4,
      borderRadius: 999,
      background: "rgba(255,255,255,0.07)",
      overflow: "hidden",
    }}>
      <div style={{
        width: `${pct}%`,
        height: "100%",
        borderRadius: 999,
        background: color,
        boxShadow: `0 0 8px ${color}80`,
        transition: "width 0.6s cubic-bezier(0.4, 0, 0.2, 1)",
      }} />
    </div>
  );
}

/* ── Main Component ── */
export default function MultiTimeframePanel({ data, loading }: MultiTimeframePanelProps) {

  /* Loading State */
  if (loading) {
    return (
      <div className="glass-card" style={{ padding: 20 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 16 }}>
          <span style={{
            width: 14, height: 14, borderRadius: "50%",
            border: "2px solid var(--ag-text-accent)",
            borderTopColor: "transparent",
            animation: "ag-spin 0.8s linear infinite",
          }} />
          <span style={{ color: "var(--ag-text-secondary)", fontSize: "0.875rem" }}>
            Menganalisis multi-timeframe...
          </span>
        </div>
        {[1, 2, 3].map((i) => (
          <div key={i} style={{
            height: 72,
            borderRadius: "var(--ag-radius-md)",
            background: "rgba(255,255,255,0.03)",
            marginBottom: 8,
            animation: "ag-shimmer 1.5s infinite",
            backgroundSize: "200% 100%",
            backgroundImage: "linear-gradient(90deg, transparent, rgba(255,255,255,0.04), transparent)",
          }} />
        ))}
      </div>
    );
  }

  if (!data) {
    return (
      <div className="glass-card" style={{ padding: 20, textAlign: "center" }}>
        <p style={{ color: "var(--ag-text-muted)", fontSize: "0.875rem" }}>
          Data Multi-Timeframe belum tersedia. Pilih ticker terlebih dahulu.
        </p>
      </div>
    );
  }

  const { timeframes, alignment } = data;

  const alignBiasConfig: Record<string, { color: string; bg: string }> = {
    fully_aligned_bullish:  { color: "#6ee7b7", bg: "rgba(16,185,129,0.10)" },
    mostly_bullish:         { color: "#7dd3fc", bg: "rgba(56,189,248,0.10)" },
    mixed:                  { color: "#fcd34d", bg: "rgba(251,191,36,0.08)" },
    bearish_dominant:       { color: "#fda4af", bg: "rgba(244,63,94,0.10)"  },
  };
  const alignStyle = alignBiasConfig[alignment.bias] ?? { color: "#94a3b8", bg: "rgba(148,163,184,0.08)" };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>

      {/* ── Alignment Summary Card ── */}
      <div className="glass-card" style={{
        padding: 18,
        background: alignStyle.bg,
        border: `1px solid ${alignStyle.color}28`,
      }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, marginBottom: 12 }}>
          <div>
            <p style={{ margin: 0, fontSize: "0.7rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--ag-text-muted)" }}>
              Multi-Timeframe Alignment
            </p>
            <p style={{ margin: "4px 0 0", fontSize: "0.875rem", fontWeight: 700, color: alignStyle.color, lineHeight: 1.4 }}>
              {alignment.label}
            </p>
          </div>
          <div style={{ textAlign: "right" }}>
            <ScorePill score={alignment.score} />
            <p style={{ margin: "5px 0 0", fontSize: "0.72rem", color: "var(--ag-text-muted)" }}>
              {alignment.bullish_timeframe_count}/3 TF Bullish
            </p>
          </div>
        </div>
        <ProgressBar value={alignment.score} />
        <div style={{
          marginTop: 12,
          padding: "10px 12px",
          borderRadius: "var(--ag-radius-sm)",
          background: alignment.trade_ready
            ? "rgba(16,185,129,0.10)"
            : "rgba(251,191,36,0.08)",
          border: `1px solid ${alignment.trade_ready ? "rgba(16,185,129,0.25)" : "rgba(251,191,36,0.2)"}`,
          fontSize: "0.78rem",
          color: alignment.trade_ready ? "#6ee7b7" : "#fcd34d",
          fontWeight: 600,
        }}>
          {alignment.trade_ready ? "✅" : "⏳"} {alignment.trade_readiness_note}
        </div>
      </div>

      {/* ── Per-Timeframe Cards ── */}
      {TF_ORDER.map((tf) => {
        const tfData = timeframes[tf];
        if (!tfData) return null;

        /* Pending realtime */
        if (tfData.status === "pending_realtime") {
          return (
            <div key={tf} className="glass-card" style={{
              padding: "14px 16px",
              opacity: 0.6,
              border: "1px dashed rgba(148,163,184,0.15)",
            }}>
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <span style={{
                  padding: "3px 10px",
                  borderRadius: "var(--ag-radius-pill)",
                  background: "rgba(148,163,184,0.08)",
                  color: "var(--ag-text-muted)",
                  fontSize: "0.7rem",
                  fontWeight: 700,
                  textTransform: "uppercase",
                  letterSpacing: "0.06em",
                  flexShrink: 0,
                }}>
                  {TF_LABELS[tf]}
                </span>
                <span style={{ fontSize: "0.78rem", color: "var(--ag-text-muted)" }}>
                  🔌 Menunggu API Real-time
                </span>
              </div>
            </div>
          );
        }

        /* Insufficient data */
        if (tfData.status === "insufficient_data") {
          return (
            <div key={tf} className="glass-card" style={{
              padding: "14px 16px",
              opacity: 0.7,
            }}>
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <span style={{
                  padding: "3px 10px",
                  borderRadius: "var(--ag-radius-pill)",
                  background: "rgba(251,191,36,0.10)",
                  color: "#fcd34d",
                  fontSize: "0.7rem",
                  fontWeight: 700,
                  textTransform: "uppercase",
                  letterSpacing: "0.06em",
                  flexShrink: 0,
                }}>
                  {TF_LABELS[tf]}
                </span>
                <span style={{ fontSize: "0.78rem", color: "#fcd34d" }}>
                  ⚠️ Data tidak cukup
                </span>
              </div>
            </div>
          );
        }

        /* OK ─ Full Card */
        const bias    = tfData.bias ?? "mixed";
        const bConf   = BIAS_CONFIG[bias] ?? BIAS_CONFIG["neutral_bearish"];
        const mConf   = MOMENTUM_CONFIG[tfData.momentum ?? "mixed"] ?? MOMENTUM_CONFIG["mixed"];
        const score   = tfData.score ?? 0;

        return (
          <div key={tf} className="glass-card" style={{
            padding: "16px 18px",
            border: `1px solid ${bConf.color}22`,
            transition: "var(--ag-transition)",
          }}>
            {/* Top Row */}
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
              {/* TF Label */}
              <span style={{
                padding: "3px 10px",
                borderRadius: "var(--ag-radius-pill)",
                background: `${bConf.color}14`,
                color: bConf.color,
                fontSize: "0.7rem",
                fontWeight: 700,
                textTransform: "uppercase",
                letterSpacing: "0.06em",
                border: `1px solid ${bConf.color}30`,
                flexShrink: 0,
              }}>
                {TF_LABELS[tf]}
              </span>

              {/* Bias */}
              <span style={{ fontSize: "0.8rem", fontWeight: 700, color: bConf.color }}>
                {bConf.emoji} {bConf.label}
              </span>

              {/* Trend */}
              {tfData.trend && (
                <span style={{
                  fontSize: "0.72rem",
                  color: "var(--ag-text-muted)",
                  marginLeft: "auto",
                  fontFamily: "'JetBrains Mono', monospace",
                }}>
                  {tfData.trend}
                </span>
              )}

              {/* Score */}
              <ScorePill score={score} />
            </div>

            {/* Progress Bar */}
            <div style={{ marginBottom: 12 }}>
              <ProgressBar value={score} />
            </div>

            {/* Info Pills Row */}
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
              {/* Momentum */}
              <span style={{
                padding: "2px 8px",
                borderRadius: "var(--ag-radius-pill)",
                background: `${mConf.color}14`,
                color: mConf.color,
                fontSize: "0.7rem",
                fontWeight: 600,
                border: `1px solid ${mConf.color}25`,
              }}>
                Momentum: {mConf.label}
              </span>

              {/* Breakout */}
              {tfData.breakout_status && (
                <span style={{
                  padding: "2px 8px",
                  borderRadius: "var(--ag-radius-pill)",
                  background: tfData.breakout_status.includes("breakout")
                    ? "rgba(16,185,129,0.12)"
                    : "rgba(148,163,184,0.08)",
                  color: tfData.breakout_status.includes("breakout")
                    ? "#6ee7b7"
                    : "var(--ag-text-muted)",
                  fontSize: "0.7rem",
                  fontWeight: 600,
                  border: "1px solid transparent",
                  textTransform: "capitalize",
                }}>
                  {tfData.breakout_status.replace(/_/g, " ")}
                </span>
              )}

              {/* MACD crossing */}
              {tfData.indicators?.macd_crossing_up && (
                <span style={{
                  padding: "2px 8px",
                  borderRadius: "var(--ag-radius-pill)",
                  background: "rgba(16,185,129,0.12)",
                  color: "#6ee7b7",
                  fontSize: "0.7rem",
                  fontWeight: 700,
                  border: "1px solid rgba(16,185,129,0.25)",
                }}>
                  ✦ MACD Cross Up
                </span>
              )}

              {/* ADX */}
              {tfData.indicators?.adx !== undefined && (
                <span style={{
                  padding: "2px 8px",
                  borderRadius: "var(--ag-radius-pill)",
                  background: "rgba(148,163,184,0.08)",
                  color: "var(--ag-text-secondary)",
                  fontSize: "0.7rem",
                  fontWeight: 600,
                  fontFamily: "'JetBrains Mono', monospace",
                }}>
                  ADX {tfData.indicators.adx.toFixed(1)}
                </span>
              )}
            </div>
          </div>
        );
      })}

      {/* ── Intraday Note ── */}
      <div style={{
        padding: "12px 14px",
        borderRadius: "var(--ag-radius-md)",
        background: "rgba(99,102,241,0.06)",
        border: "1px dashed rgba(99,102,241,0.2)",
        fontSize: "0.75rem",
        color: "#a5b4fc",
        lineHeight: 1.6,
      }}>
        <strong>🔌 Intraday (1H / 15M):</strong> Menunggu koneksi API real-time.
        Hubungkan Alpaca, Polygon.io, atau IDX direct feed untuk mengaktifkan analisis intraday.
      </div>
    </div>
  );
}
