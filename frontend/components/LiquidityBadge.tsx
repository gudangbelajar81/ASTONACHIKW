"use client";

import React from "react";

interface LiquidityWarning {
  code: string;
  severity: "EXTREME_WARNING" | "WARNING" | "CAUTION";
  message: string;
}

interface LiquidityBadgeProps {
  /** Grade: A, B, C, D, F */
  grade?: string | null;
  /** Gorengan risk level */
  riskLevel?: "none" | "low" | "medium" | "high" | "extreme" | null;
  /** True jika terdeteksi sebagai gorengan */
  isGorengan?: boolean | null;
  /** Daftar warning */
  warnings?: LiquidityWarning[] | null;
  /** Summary satu baris */
  summary?: string | null;
  /** Rekomendasi tindakan */
  recommendation?: string | null;
  /** Tampilkan hanya badge kecil (mode compact) */
  compact?: boolean;
}

const SEVERITY_ICONS: Record<string, string> = {
  EXTREME_WARNING: "🚨",
  WARNING: "⚠️",
  CAUTION: "💡",
};

const RISK_LABELS: Record<string, string> = {
  none:    "Aman",
  low:     "Risiko Rendah",
  medium:  "Gorengan",
  high:    "Gorengan Tinggi",
  extreme: "Gorengan Ekstrem",
};

/**
 * LiquidityBadge
 * Komponen UI untuk menampilkan hasil analisis likuiditas IDX.
 * Saham gorengan ditampilkan dengan WARNING jelas, bukan disembunyikan.
 */
export default function LiquidityBadge({
  grade,
  riskLevel = "none",
  isGorengan = false,
  warnings = [],
  summary,
  recommendation,
  compact = false,
}: LiquidityBadgeProps) {
  const safeGrade    = grade ?? "–";
  const safeRisk     = riskLevel ?? "none";
  const hasWarnings  = (warnings?.length ?? 0) > 0;
  const [expanded, setExpanded] = React.useState(false);

  /* ── Compact Mode: only show grade + risk badge ── */
  if (compact) {
    return (
      <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
        {/* Grade Badge */}
        <span
          className={`liq-grade liq-grade--${safeGrade}`}
          title={`Likuiditas Grade ${safeGrade}`}
          aria-label={`Likuiditas Grade ${safeGrade}`}
        >
          {safeGrade}
        </span>
        {/* Gorengan Badge */}
        {isGorengan && (
          <span className={`gorengan-badge gorengan-badge--${safeRisk}`}>
            {SEVERITY_ICONS[safeRisk === "extreme" ? "EXTREME_WARNING" : "WARNING"]}
            {RISK_LABELS[safeRisk]}
          </span>
        )}
      </div>
    );
  }

  /* ── Full Mode ── */
  return (
    <div
      style={{
        borderRadius: "var(--ag-radius-md)",
        border: `1px solid ${
          safeRisk === "extreme" ? "rgba(244,63,94,0.3)"
          : safeRisk === "high"    ? "rgba(244,63,94,0.2)"
          : safeRisk === "medium"  ? "rgba(249,115,22,0.2)"
          : "var(--ag-border-glass)"
        }`,
        background: `${
          safeRisk === "extreme" ? "rgba(244,63,94,0.07)"
          : safeRisk === "high"    ? "rgba(244,63,94,0.05)"
          : safeRisk === "medium"  ? "rgba(249,115,22,0.05)"
          : "var(--ag-bg-glass)"
        }`,
        overflow: "hidden",
      }}
      role="region"
      aria-label="Analisis Likuiditas"
    >
      {/* ── Header Row ── */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 10,
          padding: "12px 14px",
          cursor: hasWarnings ? "pointer" : "default",
        }}
        onClick={() => hasWarnings && setExpanded((e) => !e)}
        role={hasWarnings ? "button" : undefined}
        aria-expanded={hasWarnings ? expanded : undefined}
      >
        {/* Grade Badge */}
        <span className={`liq-grade liq-grade--${safeGrade}`}>
          {safeGrade}
        </span>

        {/* Summary text */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <p style={{
            margin: 0,
            fontSize: "0.8rem",
            color: "var(--ag-text-primary)",
            fontWeight: 600,
            lineHeight: 1.4,
            whiteSpace: "nowrap",
            overflow: "hidden",
            textOverflow: "ellipsis",
          }}>
            {summary ?? `Likuiditas Grade ${safeGrade}`}
          </p>
        </div>

        {/* Gorengan Badge */}
        {safeRisk !== "none" && (
          <span className={`gorengan-badge gorengan-badge--${safeRisk}`}>
            {SEVERITY_ICONS[
              safeRisk === "extreme" || safeRisk === "high"
                ? "EXTREME_WARNING"
                : "WARNING"
            ]}
            {RISK_LABELS[safeRisk]}
          </span>
        )}

        {/* Expand chevron */}
        {hasWarnings && (
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

      {/* ── Expanded Warning List ── */}
      {expanded && hasWarnings && (
        <div
          style={{
            padding: "0 14px 14px",
            display: "flex",
            flexDirection: "column",
            gap: 6,
            animation: "ag-fade-in 0.2s ease",
          }}
        >
          {warnings!.map((w, i) => (
            <div
              key={`${w.code}-${i}`}
              className={`warning-box warning-box--${
                w.severity === "EXTREME_WARNING" ? "extreme"
                : w.severity === "WARNING"       ? "warning"
                : "caution"
              }`}
              role="alert"
              aria-live="polite"
            >
              <span style={{ flexShrink: 0, fontSize: "1rem" }}>
                {SEVERITY_ICONS[w.severity]}
              </span>
              <span style={{ fontSize: "0.78rem", lineHeight: 1.55 }}>
                {w.message}
              </span>
            </div>
          ))}

          {/* Recommendation */}
          {recommendation && (
            <div style={{
              marginTop: 4,
              padding: "10px 12px",
              borderRadius: "var(--ag-radius-sm)",
              background: "rgba(99, 102, 241, 0.08)",
              border: "1px solid rgba(99, 102, 241, 0.18)",
              fontSize: "0.78rem",
              color: "#a5b4fc",
              lineHeight: 1.55,
            }}>
              <span style={{ fontWeight: 700 }}>💡 Rekomendasi: </span>
              {recommendation}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
