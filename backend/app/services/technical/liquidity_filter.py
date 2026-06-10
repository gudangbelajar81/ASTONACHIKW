"""
liquidity_filter.py
===================
IDX Liquidity & Gorengan WARNING System.

Filosofi (sesuai arahan arsitek):
  - Saham gorengan TIDAK diblokir/dibuang dari hasil screening.
  - Saham gorengan TETAP ditampilkan, namun diberi label WARNING yang jelas
    beserta alasan spesifik mengapa saham tersebut dianggap berisiko tinggi.
  - Trader profesional dapat menggunakan informasi ini untuk membuat keputusan
    sendiri dengan penuh kesadaran risiko.

Threshold IDX (standar profesional):
  - Min avg value traded 20 hari: Rp 5 Miliar (soft), Rp 10 Miliar (ideal)
  - Min avg volume 20 hari: 500.000 lot
  - Spread detection: close vs VWAP > 5% = suspicious
  - Volume spike tanpa fundamental: volume_vs_20d > 5x = pump signal
  - Micro-cap proxy: avg_value < Rp 1 Miliar = extreme caution
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from backend.app.services.technical.common import safe_float


# ─────────────────────────── Thresholds ────────────────────────────

# Nilai transaksi rata-rata 20 hari (Rupiah)
THRESHOLD_VALUE_EXTREME_CAUTION = 1_000_000_000     # < Rp 1 M  → EXTREME WARNING
THRESHOLD_VALUE_LOW_LIQUIDITY   = 5_000_000_000     # < Rp 5 M  → WARNING
THRESHOLD_VALUE_IDEAL           = 10_000_000_000    # >= Rp 10 M → Likuiditas sehat

# Volume rata-rata 20 hari (lot)
THRESHOLD_VOLUME_LOW            = 500_000           # < 500K lot → WARNING
THRESHOLD_VOLUME_MINIMAL        = 100_000           # < 100K lot → EXTREME WARNING

# Deteksi aktivitas tidak wajar
THRESHOLD_PUMP_VOLUME_RATIO     = 5.0               # Volume spike > 5x avg → pump signal
THRESHOLD_SPREAD_SUSPICIOUS_PCT = 0.05              # |close - VWAP| / VWAP > 5% → suspicious
THRESHOLD_ILLIQUID_DAYS_RATIO   = 0.20              # > 20% hari tanpa transaksi → illiquid


# ─────────────────────────── Data Classes ──────────────────────────

@dataclass
class LiquidityWarning:
    """Representasi satu peringatan likuiditas."""
    code: str                   # Kode unik peringatan (e.g., "LOW_VALUE_TRADED")
    severity: str               # "EXTREME_WARNING" | "WARNING" | "CAUTION"
    message: str                # Pesan human-readable dalam bahasa Indonesia
    value: Any = None           # Nilai aktual yang memicu warning (opsional)


@dataclass
class LiquidityResult:
    """Hasil lengkap analisis likuiditas untuk satu saham."""
    passed: bool                                    # True jika lolos threshold minimal
    liquidity_grade: str                            # "A" | "B" | "C" | "D" | "F"
    is_gorengan: bool                               # True jika terdeteksi sebagai saham gorengan
    gorengan_risk_level: str                        # "none" | "low" | "medium" | "high" | "extreme"
    warnings: list[LiquidityWarning] = field(default_factory=list)

    # Metrics
    avg_value_20d: float = 0.0
    avg_volume_20d: float = 0.0
    latest_value: float = 0.0
    volume_vs_20d_avg: float = 0.0
    zero_volume_days_ratio: float = 0.0
    spread_from_vwap_pct: float = 0.0

    # Summary
    summary: str = ""
    recommendation: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "liquidity_grade": self.liquidity_grade,
            "is_gorengan": self.is_gorengan,
            "gorengan_risk_level": self.gorengan_risk_level,
            "warnings": [
                {
                    "code": w.code,
                    "severity": w.severity,
                    "message": w.message,
                    "value": w.value,
                }
                for w in self.warnings
            ],
            "metrics": {
                "avg_value_20d": round(self.avg_value_20d, 2),
                "avg_volume_20d": round(self.avg_volume_20d, 2),
                "latest_value": round(self.latest_value, 2),
                "volume_vs_20d_avg": round(self.volume_vs_20d_avg, 3),
                "zero_volume_days_ratio": round(self.zero_volume_days_ratio, 3),
                "spread_from_vwap_pct": round(self.spread_from_vwap_pct, 4),
            },
            "summary": self.summary,
            "recommendation": self.recommendation,
            "warning_count": len(self.warnings),
            "has_warnings": len(self.warnings) > 0,
        }


# ─────────────────────────── Core Engine ───────────────────────────

def analyze_liquidity(df: pd.DataFrame, symbol: str = "") -> LiquidityResult:
    """
    Analisis likuiditas IDX untuk satu saham.

    Parameters
    ----------
    df : pd.DataFrame
        OHLCV DataFrame dengan kolom: date, open, high, low, close, volume.
        Minimal 20 baris data.
    symbol : str
        Ticker saham (untuk pesan warning yang lebih informatif).

    Returns
    -------
    LiquidityResult
        Objek hasil analisis dengan semua flag, warning, dan grade.
    """
    warnings: list[LiquidityWarning] = []

    if len(df) < 20:
        return LiquidityResult(
            passed=False,
            liquidity_grade="F",
            is_gorengan=False,
            gorengan_risk_level="none",
            warnings=[LiquidityWarning(
                code="INSUFFICIENT_DATA",
                severity="EXTREME_WARNING",
                message=f"{symbol}: Data historis kurang dari 20 hari, tidak dapat menganalisis likuiditas.",
            )],
            summary="Data tidak cukup untuk analisis likuiditas.",
            recommendation="Hindari saham ini hingga data historis mencukupi.",
        )

    recent = df.tail(20).copy()
    close = recent["close"].astype(float)
    volume = recent["volume"].astype(float)
    high = recent["high"].astype(float)
    low = recent["low"].astype(float)

    # ── Metric Calculation ──
    avg_volume_20d = safe_float(volume.mean())
    avg_close_20d = safe_float(close.mean())
    avg_value_20d = avg_volume_20d * avg_close_20d

    latest_volume = safe_float(volume.iloc[-1])
    latest_close = safe_float(close.iloc[-1])
    latest_value = latest_volume * latest_close

    volume_vs_20d = latest_volume / avg_volume_20d if avg_volume_20d > 0 else 0.0

    # Zero volume days
    zero_days = int((volume <= 0).sum())
    zero_ratio = zero_days / len(recent)

    # VWAP calculation (sederhana: typical price * volume / total volume)
    typical = (high + low + close) / 3
    total_volume = safe_float(volume.sum())
    vwap = safe_float((typical * volume).sum() / total_volume) if total_volume > 0 else latest_close
    spread_from_vwap_pct = abs(latest_close - vwap) / vwap if vwap > 0 else 0.0

    # ── Warning Checks ──────────────────────────────────────────────

    # 1. Nilai transaksi sangat rendah
    if avg_value_20d < THRESHOLD_VALUE_EXTREME_CAUTION:
        warnings.append(LiquidityWarning(
            code="EXTREME_LOW_VALUE_TRADED",
            severity="EXTREME_WARNING",
            message=(
                f"⚠️ EXTREME: Rata-rata nilai transaksi 20 hari sangat rendah "
                f"(Rp {avg_value_20d:,.0f}). Saham ini sangat tidak likuid dan "
                f"sangat rentan terhadap manipulasi harga."
            ),
            value=round(avg_value_20d, 2),
        ))
    elif avg_value_20d < THRESHOLD_VALUE_LOW_LIQUIDITY:
        warnings.append(LiquidityWarning(
            code="LOW_VALUE_TRADED",
            severity="WARNING",
            message=(
                f"⚠️ WARNING: Rata-rata nilai transaksi 20 hari di bawah Rp 5 Miliar "
                f"(Rp {avg_value_20d:,.0f}). Likuiditas rendah, spread bid-ask dapat melebar."
            ),
            value=round(avg_value_20d, 2),
        ))

    # 2. Volume rata-rata rendah
    if avg_volume_20d < THRESHOLD_VOLUME_MINIMAL:
        warnings.append(LiquidityWarning(
            code="EXTREME_LOW_VOLUME",
            severity="EXTREME_WARNING",
            message=(
                f"⚠️ EXTREME: Volume rata-rata 20 hari sangat rendah "
                f"({avg_volume_20d:,.0f} lot). Risiko tidak dapat keluar posisi sangat tinggi."
            ),
            value=round(avg_volume_20d, 2),
        ))
    elif avg_volume_20d < THRESHOLD_VOLUME_LOW:
        warnings.append(LiquidityWarning(
            code="LOW_VOLUME",
            severity="WARNING",
            message=(
                f"⚠️ WARNING: Volume rata-rata 20 hari di bawah 500.000 lot "
                f"({avg_volume_20d:,.0f} lot). Sulit keluar posisi dalam jumlah besar."
            ),
            value=round(avg_volume_20d, 2),
        ))

    # 3. Hari tanpa transaksi (illiquid days)
    if zero_ratio > THRESHOLD_ILLIQUID_DAYS_RATIO:
        warnings.append(LiquidityWarning(
            code="ILLIQUID_DAYS_DETECTED",
            severity="EXTREME_WARNING",
            message=(
                f"⚠️ EXTREME: {zero_days} dari {len(recent)} hari terakhir tidak ada transaksi "
                f"({zero_ratio*100:.1f}%). Saham ini sangat tidak aktif."
            ),
            value={"zero_days": zero_days, "ratio": round(zero_ratio, 3)},
        ))

    # 4. Pump signal - Volume spike mendadak
    if volume_vs_20d >= THRESHOLD_PUMP_VOLUME_RATIO and avg_value_20d < THRESHOLD_VALUE_LOW_LIQUIDITY:
        warnings.append(LiquidityWarning(
            code="PUMP_SIGNAL_VOLUME_SPIKE",
            severity="EXTREME_WARNING",
            message=(
                f"🚨 PUMP SIGNAL: Volume hari ini {volume_vs_20d:.1f}x di atas rata-rata 20 hari "
                f"pada saham yang biasanya tidak likuid. Ini adalah tanda klasik pump-and-dump."
            ),
            value=round(volume_vs_20d, 2),
        ))
    elif volume_vs_20d >= THRESHOLD_PUMP_VOLUME_RATIO:
        warnings.append(LiquidityWarning(
            code="UNUSUAL_VOLUME_SPIKE",
            severity="WARNING",
            message=(
                f"⚠️ CAUTION: Volume hari ini {volume_vs_20d:.1f}x di atas rata-rata 20 hari. "
                f"Volume spike luar biasa, konfirmasi dengan berita fundamental."
            ),
            value=round(volume_vs_20d, 2),
        ))

    # 5. Spread dari VWAP mencurigakan
    if spread_from_vwap_pct > THRESHOLD_SPREAD_SUSPICIOUS_PCT:
        warnings.append(LiquidityWarning(
            code="SUSPICIOUS_PRICE_VWAP_SPREAD",
            severity="CAUTION",
            message=(
                f"⚠️ CAUTION: Harga penutupan menyimpang {spread_from_vwap_pct*100:.1f}% dari VWAP. "
                f"Indikasi terjadi manipulasi harga intraday atau bid-ask spread yang sangat lebar."
            ),
            value=round(spread_from_vwap_pct, 4),
        ))

    # ── Determine Gorengan Status ───────────────────────────────────
    extreme_warnings = [w for w in warnings if w.severity == "EXTREME_WARNING"]
    regular_warnings = [w for w in warnings if w.severity == "WARNING"]

    is_gorengan = len(extreme_warnings) >= 1 or len(regular_warnings) >= 2

    if len(extreme_warnings) >= 2:
        gorengan_risk = "extreme"
    elif len(extreme_warnings) == 1:
        gorengan_risk = "high"
    elif len(regular_warnings) >= 2:
        gorengan_risk = "medium"
    elif len(regular_warnings) == 1 or len(warnings) > 0:
        gorengan_risk = "low"
    else:
        gorengan_risk = "none"

    # ── Liquidity Grade ─────────────────────────────────────────────
    if avg_value_20d >= THRESHOLD_VALUE_IDEAL and avg_volume_20d >= THRESHOLD_VOLUME_LOW and not is_gorengan:
        grade = "A"
    elif avg_value_20d >= THRESHOLD_VALUE_LOW_LIQUIDITY and not is_gorengan:
        grade = "B"
    elif avg_value_20d >= THRESHOLD_VALUE_EXTREME_CAUTION and gorengan_risk in ("none", "low"):
        grade = "C"
    elif avg_value_20d >= THRESHOLD_VALUE_EXTREME_CAUTION:
        grade = "D"
    else:
        grade = "F"

    passed = grade in ("A", "B")

    # ── Summary & Recommendation ────────────────────────────────────
    symbol_label = f"[{symbol}] " if symbol else ""

    if gorengan_risk == "none":
        summary = f"{symbol_label}Likuiditas sehat. Grade {grade}."
        recommendation = "Saham layak ditransaksikan. Lanjutkan analisis teknikal."
    elif gorengan_risk == "low":
        summary = f"{symbol_label}⚠️ Likuiditas cukup, namun ada 1 catatan risiko. Grade {grade}."
        recommendation = "Gunakan position sizing lebih kecil dan pantau spread bid-ask."
    elif gorengan_risk == "medium":
        summary = f"{symbol_label}⚠️ GORENGAN RISK MEDIUM - Beberapa indikator likuiditas merah. Grade {grade}."
        recommendation = "Hati-hati! Batasi eksposur. Gunakan stop loss ketat dan hindari posisi besar."
    elif gorengan_risk == "high":
        summary = f"{symbol_label}🚨 GORENGAN RISK HIGH - Saham ini terindikasi kuat sebagai saham gorengan. Grade {grade}."
        recommendation = (
            "PERINGATAN KERAS: Saham ini sangat berisiko. Jika tetap ingin bertransaksi, "
            "gunakan modal yang siap hilang 100% dan exit secepat mungkin."
        )
    else:
        summary = f"{symbol_label}🚨 GORENGAN EXTREME - Saham ini sangat berbahaya! Grade {grade}."
        recommendation = (
            "JANGAN MASUK! Semua indikator menunjukkan risiko manipulasi ekstrem. "
            "Potensi pump-and-dump sangat tinggi. Sangat tidak direkomendasikan untuk trading."
        )

    return LiquidityResult(
        passed=passed,
        liquidity_grade=grade,
        is_gorengan=is_gorengan,
        gorengan_risk_level=gorengan_risk,
        warnings=warnings,
        avg_value_20d=avg_value_20d,
        avg_volume_20d=avg_volume_20d,
        latest_value=latest_value,
        volume_vs_20d_avg=volume_vs_20d,
        zero_volume_days_ratio=zero_ratio,
        spread_from_vwap_pct=spread_from_vwap_pct,
        summary=summary,
        recommendation=recommendation,
    )


def quick_liquidity_flag(df: pd.DataFrame, symbol: str = "") -> dict[str, Any]:
    """
    Shortcut: Hanya kembalikan flag dan summary untuk integrasi cepat
    ke dalam screener tanpa overhead data penuh.
    """
    result = analyze_liquidity(df, symbol)
    return {
        "liquidity_grade": result.liquidity_grade,
        "is_gorengan": result.is_gorengan,
        "gorengan_risk_level": result.gorengan_risk_level,
        "has_warnings": result.has_warnings if hasattr(result, "has_warnings") else len(result.warnings) > 0,
        "warning_count": len(result.warnings),
        "summary": result.summary,
    }
