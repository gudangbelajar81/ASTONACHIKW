"use client";

import React, { useState } from "react";

interface DistributionSignal {
  type: string;
  severity: "EXTREME_WARNING" | "WARNING" | "CAUTION";
  message: string;
  value?: unknown;
}

interface DistributionData {
  is_distributing: boolean;
  distribution_score: number;
  risk_level: "none" | "low" | "medium" | "high" | "extreme";
  signals: DistributionSignal[];
  mdd_count: number;
  obv_divergence: boolean;
  volume_dry_up_on_rally: boolean;
  selling_pressure_score: number;
  summary: string;
  recommendation: string;
}

interface DistributionAlertProps {
  data: DistributionData | null;
  compact?: boolean;
}

const RISK_CONFIG = {
  none:    { label: "Bersih",        color: "#6ee7b7", bg: "rgba(16,185,129,0.08)",  borderColor: "rgba(16,185,129,0.20)", icon: "✅" },
  low:     { label: "Risiko Rendah", color: "#7dd3fc", bg: "rgba(56,189,248,0.07)",  borderColor: "rgba(56,189,248,0.18)", icon: "💧" },
  medium:  { label: "Distribusi",    color: "#fcd34d", bg: "rgba(251,191,36,0.08)",  borderColor: "rgba(251,191,36,0.22)", icon: "⚠️" },
  high:    { label: "Distribusi 🚨", color: "#fdba74", bg: "rgba(249,115,22,0.10)",  borderColor: "rgba(249,115,22,0.30)", icon: "🚨" },
  extreme: { label: "EKSTREM 🚨",    color: "#fda4af", bg: "rgba(244,63,94,0.12)",   borderColor: "rgba(244,63,94,0.40)",  icon: "🔴" },
};

const SEVERITY_ICONS = {
  EXTREME_WARNING: "🚨",
  WARNING: "⚠️",
  CAUTION: "💡",
};

function ScoreGauge({ score, riskLevel }: { score: number; riskLevel: string }) {
  const conf = RISK_CONFIG[riskLevel as keyof typeof RISK_CONFIG] ?? RISK_CONFIG.none;
  const pct  = Math.min(100, Math.max(0, score));
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 4 }}>
      {/* Arc / Half Donut simplified as a number */}
      <div style={{
        width: 60,
        height: 60,
        borderRadius: "50%",
        background: `conic-gradient(${conf.color} ${pct * 3.6}deg, rgba(255,255,255,0.05) 0deg)`,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        position: "relative",
        boxShadow: score >= 55 ? `0 0 16px ${conf.color}50` : "none",
        transition: "box-shadow 0.3s",
      }}>
        <div style={{
          width: 48,
          height: 48,
          borderRadius: "50%",
          background: "var(--ag-bg-elevated)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          flexDirection: "column",
        }}>
          <span style={{
            fontSize: "1.1rem",
            fontWeight: 900,
            fontFamily: "'JetBrains Mono', monospace",
            color: conf.color,
            lineHeight: 1,
          }}>
            {score}
          </span>
        </div>
      </div>
      <span style={{ fontSize: "0.65rem", color: "var(--ag-text-muted)", textTransform: "uppercase", letterSpacing: "0.06em" }}>
        Distribusi
      </span>
    </div>
  );
}

export default function DistributionAlert({ data, compact = false }: DistributionAlertProps) {
  const [expanded, setExpanded] = useState(false);

  if (!data) return null;

  const conf = RISK_CONFIG[data.risk_level] ?? RISK_CONFIG.none;

  /* ── Compact Mode ── */
  if (compact) {
    return (
      <div style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
        padding: "3px 10px",
        borderRadius: "var(--ag-radius-pill)",
        background: conf.bg,
        border: `1px solid ${conf.borderColor}`,
        fontSize: "0.7rem",
        fontWeight: 800,
        color: conf.color,
        textTransform: "uppercase",
        letterSpacing: "0.06em",
      }}
        title={data.summary}
        role="status"
      >
        <span>{conf.icon}</span>
        <span>{conf.label}</span>
        <span style={{ fontFamily: "'JetBrains Mono', monospace", opacity: 0.8 }}>
          {data.distribution_score}/100
        </span>
      </div>
    );
  }

  /* ── Full Mode ── */
  const indicators = [
    { label: "MDD",          value: data.mdd_count,          unit: "hari",       active: data.mdd_count >= 4  },
    { label: "OBV Diverg.",  value: data.obv_divergence ? "Ya" : "Tidak",        active: data.obv_divergence  },
    { label: "Volume Dry-Up",value: data.volume_dry_up_on_rally ? "Ya" : "Tidak",active: data.volume_dry_up_on_rally },
    { label: "Sell Pressure",value: `${data.selling_pressure_score}%`,           active: data.selling_pressure_score > 60 },
  ];

  return (
    <div
      className="glass-card"
      style={{
        overflow: "hidden",
        border: `1px solid ${conf.borderColor}`,
        background: conf.bg,
        animation: data.risk_level === "extreme" ? "ag-danger-pulse 2s infinite" : undefined,
      }}
      role="region"
      aria-label="Analisis Distribusi"
    >
      {/* ── Header ── */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 14,
          padding: "16px 18px",
          cursor: data.signals.length > 0 ? "pointer" : "default",
        }}
        onClick={() => data.signals.length > 0 && setExpanded((e) => !e)}
        role={data.signals.length > 0 ? "button" : undefined}
        aria-expanded={data.signals.length > 0 ? expanded : undefined}
      >
        {/* Gauge */}
        <ScoreGauge score={data.distribution_score} riskLevel={data.risk_level} />

        {/* Info */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
            <span style={{
              padding: "3px 10px",
              borderRadius: "var(--ag-radius-pill)",
              background: `${conf.color}18`,
              color: conf.color,
              fontSize: "0.7rem",
              fontWeight: 800,
              textTransform: "uppercase",
              letterSpacing: "0.06em",
              border: `1px solid ${conf.color}30`,
            }}>
              {conf.icon} {conf.label}
            </span>
          </div>
          <p style={{
            margin: 0,
            fontSize: "0.8rem",
            color: "var(--ag-text-secondary)",
            lineHeight: 1.5,
            display: "-webkit-box",
            WebkitLineClamp: 2,
            WebkitBoxOrient: "vertical",
            overflow: "hidden",
          }}>
            {data.summary}
          </p>
        </div>

        {/* Expand Arrow */}
        {data.signals.length > 0 && (
          <span style={{
            color: "var(--ag-text-muted)",
            fontSize: "0.75rem",
            transition: "transform 0.2s",
            transform: expanded ? "rotate(180deg)" : "rotate(0deg)",
            flexShrink: 0,
          }}>
            ▾
          </span>
        )}
      </div>

      {/* ── Indicator Grid ── */}
      <div style={{
        display: "grid",
        gridTemplateColumns: "repeat(4, 1fr)",
        gap: 1,
        background: "rgba(255,255,255,0.04)",
        borderTop: "1px solid rgba(255,255,255,0.05)",
        borderBottom: expanded ? "1px solid rgba(255,255,255,0.05)" : undefined,
      }}>
        {indicators.map((ind) => (
          <div key={ind.label} style={{
            padding: "10px 12px",
            background: ind.active
              ? `${conf.color}08`
              : "rgba(12,21,40,0.6)",
            textAlign: "center",
          }}>
            <p style={{
              margin: 0,
              fontSize: "0.65rem",
              color: "var(--ag-text-muted)",
              textTransform: "uppercase",
              letterSpacing: "0.06em",
              marginBottom: 3,
            }}>
              {ind.label}
            </p>
            <p style={{
              margin: 0,
              fontSize: "0.85rem",
              fontWeight: 700,
              fontFamily: "'JetBrains Mono', monospace",
              color: ind.active ? conf.color : "var(--ag-text-secondary)",
            }}>
              {String(ind.value)}
            </p>
          </div>
        ))}
      </div>

      {/* ── Expanded Signal Detail ── */}
      {expanded && (
        <div
          style={{
            padding: "14px 18px",
            display: "flex",
            flexDirection: "column",
            gap: 8,
            animation: "ag-fade-in 0.2s ease",
          }}
        >
          {data.signals.map((sig, i) => (
            <div
              key={`${sig.type}-${i}`}
              className={`warning-box warning-box--${
                sig.severity === "EXTREME_WARNING" ? "extreme"
                : sig.severity === "WARNING"       ? "warning"
                : "caution"
              }`}
              role="alert"
            >
              <span style={{ flexShrink: 0, fontSize: "1rem" }}>
                {SEVERITY_ICONS[sig.severity]}
              </span>
              <span style={{ fontSize: "0.78rem", lineHeight: 1.55 }}>
                {sig.message}
              </span>
            </div>
          ))}

          {/* Recommendation box */}
          <div style={{
            marginTop: 4,
            padding: "12px 14px",
            borderRadius: "var(--ag-radius-md)",
            background: "rgba(99,102,241,0.08)",
            border: "1px solid rgba(99,102,241,0.18)",
            fontSize: "0.8rem",
            color: "#a5b4fc",
            fontWeight: 600,
            lineHeight: 1.6,
          }}>
            <span>💡 </span>
            {data.recommendation}
          </div>
        </div>
      )}
    </div>
  );
}
