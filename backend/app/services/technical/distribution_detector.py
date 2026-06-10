"""
distribution_detector.py
=========================
Deteksi Pola Distribusi & Tekanan Jual (Distribution Detection Engine).

Tanda-tanda distribusi adalah sinyal bahwa "smart money" sedang keluar
dari posisi dan mendistribusikan saham ke publik (retail) sebelum harga
jatuh. Engine ini mendeteksi pola tersebut secara kuantitatif.

Pola yang dideteksi:
1. Volume Dry-Up saat harga naik   → Akumulasi/distribusi meragukan
2. Volume Spike saat harga turun   → Tekanan jual institusional
3. Distribution Candle Patterns    → Upper shadow panjang, lower shadow pendek
4. Divergence: Harga naik, OBV turun → Smart money keluar
5. Price Stalling at Resistance    → Harga mentok tanpa kekuatan
6. Multiple Distribution Days (MDDs) → Banyak hari distribusi beruntun
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd
import numpy as np

from backend.app.services.technical.common import safe_float, clamp, score_0_100


# ─────────────────────────── Data Class ────────────────────────────

@dataclass
class DistributionResult:
    """Hasil analisis distribusi untuk satu saham."""
    is_distributing: bool               # True jika terdeteksi distribusi signifikan
    distribution_score: int             # 0–100 (makin tinggi makin berbahaya)
    risk_level: str                     # "none" | "low" | "medium" | "high" | "extreme"
    signals: list[dict[str, Any]] = field(default_factory=list)  # Sinyal yang terdeteksi
    mdd_count: int = 0                  # Jumlah Multiple Distribution Days
    obv_divergence: bool = False        # True jika ada divergence OBV vs harga
    volume_dry_up_on_rally: bool = False
    selling_pressure_score: int = 0     # 0–100
    summary: str = ""
    recommendation: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_distributing": self.is_distributing,
            "distribution_score": self.distribution_score,
            "risk_level": self.risk_level,
            "signals": self.signals,
            "mdd_count": self.mdd_count,
            "obv_divergence": self.obv_divergence,
            "volume_dry_up_on_rally": self.volume_dry_up_on_rally,
            "selling_pressure_score": self.selling_pressure_score,
            "summary": self.summary,
            "recommendation": self.recommendation,
        }


# ─────────────────────────── Core Engine ───────────────────────────

def _compute_obv(df: pd.DataFrame) -> pd.Series:
    """Hitung On-Balance Volume (OBV) dari OHLCV DataFrame."""
    close = df["close"].astype(float)
    volume = df["volume"].astype(float)
    direction = close.diff().apply(lambda x: 1 if x > 0 else (-1 if x < 0 else 0))
    return (direction * volume).cumsum()


def _upper_shadow_ratio(df: pd.DataFrame) -> pd.Series:
    """
    Rasio upper shadow terhadap range candle.
    Nilai tinggi (> 0.6) menandakan tekanan jual di atas.
    """
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    open_ = df["open"].astype(float)
    close = df["close"].astype(float)
    body_top = pd.concat([open_, close], axis=1).max(axis=1)
    candle_range = (high - low).replace(0, 0.0001)
    return (high - body_top) / candle_range


def detect_distribution(df: pd.DataFrame, lookback: int = 20) -> DistributionResult:
    """
    Analisis distribusi pada data OHLCV.

    Parameters
    ----------
    df : pd.DataFrame
        Data OHLCV. Minimal 30 baris.
    lookback : int
        Jumlah hari terakhir yang dianalisis (default 20 hari kerja = 1 bulan).

    Returns
    -------
    DistributionResult
    """
    signals: list[dict[str, Any]] = []

    if len(df) < 30:
        return DistributionResult(
            is_distributing=False,
            distribution_score=0,
            risk_level="none",
            summary="Data tidak cukup untuk analisis distribusi (butuh min 30 candle).",
            recommendation="Kumpulkan lebih banyak data historis.",
        )

    df_sorted = df.sort_values("date").reset_index(drop=True)
    recent = df_sorted.tail(lookback).copy().reset_index(drop=True)
    full = df_sorted.copy()

    close = recent["close"].astype(float)
    high = recent["high"].astype(float)
    low = recent["low"].astype(float)
    volume = recent["volume"].astype(float)
    open_ = recent["open"].astype(float)

    avg_volume = safe_float(full["volume"].astype(float).tail(60).mean())
    last_close = safe_float(close.iloc[-1])
    first_close = safe_float(close.iloc[0])

    # ── 1. Multiple Distribution Days (MDD) ────────────────────────
    # Hari di mana harga turun DENGAN volume di atas rata-rata
    down_days_high_vol = (
        (close < open_) &  # bearish candle
        (volume > avg_volume * 1.2)  # volume di atas rata-rata
    )
    mdd_count = int(down_days_high_vol.sum())
    if mdd_count >= 4:
        severity = "EXTREME_WARNING" if mdd_count >= 7 else "WARNING"
        signals.append({
            "type": "MULTIPLE_DISTRIBUTION_DAYS",
            "severity": severity,
            "message": f"🚨 {mdd_count} Distribution Day terdeteksi dalam {lookback} hari terakhir. Smart money kemungkinan keluar.",
            "value": mdd_count,
        })

    # ── 2. Volume Dry-Up on Rally ───────────────────────────────────
    # Harga naik tapi volume di bawah rata-rata
    up_days = close > open_
    up_days_low_vol = up_days & (volume < avg_volume * 0.8)
    rally_dry_ratio = int(up_days_low_vol.sum()) / max(int(up_days.sum()), 1)
    volume_dry_up_on_rally = rally_dry_ratio >= 0.5

    if volume_dry_up_on_rally:
        signals.append({
            "type": "VOLUME_DRY_UP_ON_RALLY",
            "severity": "WARNING",
            "message": (
                f"⚠️ {rally_dry_ratio*100:.0f}% hari naik terjadi dengan volume rendah. "
                f"Kenaikan harga tidak didukung volume — tanda distribusi."
            ),
            "value": round(rally_dry_ratio, 3),
        })

    # ── 3. OBV Divergence ───────────────────────────────────────────
    # Harga naik, tapi OBV turun (divergence bearish)
    obv = _compute_obv(df_sorted)
    obv_recent = obv.tail(lookback)
    obv_trend = safe_float(obv_recent.iloc[-1]) - safe_float(obv_recent.iloc[0])
    price_trend = last_close - first_close
    obv_divergence = price_trend > 0 and obv_trend < 0

    if obv_divergence:
        signals.append({
            "type": "OBV_BEARISH_DIVERGENCE",
            "severity": "WARNING",
            "message": (
                f"⚠️ Divergence OBV vs Harga: Harga naik {price_trend:.2f} "
                f"namun OBV turun {obv_trend:.0f}. Smart money kemungkinan keluar diam-diam."
            ),
            "value": {"price_change": round(price_trend, 4), "obv_change": round(obv_trend, 2)},
        })

    # ── 4. Upper Shadow Dominance ───────────────────────────────────
    # Banyak candle dengan upper shadow panjang = tekanan jual di atas
    upper_shadow = _upper_shadow_ratio(recent)
    heavy_upper_shadow_ratio = float((upper_shadow > 0.55).mean())
    if heavy_upper_shadow_ratio >= 0.35:
        signals.append({
            "type": "UPPER_SHADOW_DOMINANCE",
            "severity": "CAUTION",
            "message": (
                f"⚠️ {heavy_upper_shadow_ratio*100:.0f}% candle memiliki upper shadow dominan. "
                f"Tekanan jual konsisten di area harga atas."
            ),
            "value": round(heavy_upper_shadow_ratio, 3),
        })

    # ── 5. Price Stalling at Resistance ─────────────────────────────
    # Harga naik ke level resistansi tetapi tidak bisa break
    resistance = safe_float(high.max())
    current_distance_to_resistance = (resistance - last_close) / resistance if resistance > 0 else 0
    is_stalling = (
        current_distance_to_resistance < 0.03  # Harga sangat dekat resistance
        and safe_float(high.tail(5).std()) < safe_float(high.std()) * 0.4  # Volatilitas menyempit
    )
    if is_stalling:
        signals.append({
            "type": "PRICE_STALLING_AT_RESISTANCE",
            "severity": "CAUTION",
            "message": (
                f"⚠️ Harga stalling di area resistance {resistance:.2f}. "
                f"Kegagalan breakout berulang dapat memicu distribusi."
            ),
            "value": round(resistance, 4),
        })

    # ── 6. Selling Pressure Score ────────────────────────────────────
    # Komposit tekanan jual berdasarkan volume-weighted
    down_volume = volume[close < open_].sum()
    up_volume = volume[close >= open_].sum()
    total_volume = safe_float(volume.sum())
    selling_pressure_score = score_0_100(
        clamp(safe_float(down_volume) / total_volume if total_volume > 0 else 0.5)
    )

    # ── Final Scoring ────────────────────────────────────────────────
    score = 0
    score += min(40, mdd_count * 6)        # MDD berkontribusi max 40 poin
    score += 20 if obv_divergence else 0
    score += 15 if volume_dry_up_on_rally else 0
    score += 10 if heavy_upper_shadow_ratio >= 0.35 else 0
    score += 5 if is_stalling else 0
    score += int(clamp(selling_pressure_score / 100) * 10)
    distribution_score = min(100, score)

    # ── Risk Level ───────────────────────────────────────────────────
    if distribution_score >= 75:
        risk_level = "extreme"
        is_distributing = True
    elif distribution_score >= 55:
        risk_level = "high"
        is_distributing = True
    elif distribution_score >= 35:
        risk_level = "medium"
        is_distributing = True
    elif distribution_score >= 15:
        risk_level = "low"
        is_distributing = False
    else:
        risk_level = "none"
        is_distributing = False

    # ── Summary & Recommendation ─────────────────────────────────────
    if risk_level == "none":
        summary = f"Tidak ada tanda distribusi signifikan. Skor: {distribution_score}/100."
        recommendation = "Saham dalam kondisi akumulasi atau netral. Aman untuk analisis lanjut."
    elif risk_level == "low":
        summary = f"⚠️ Sedikit sinyal distribusi terdeteksi. Skor: {distribution_score}/100."
        recommendation = "Waspadai volume pada hari naik. Gunakan stop loss yang disiplin."
    elif risk_level == "medium":
        summary = f"⚠️ DISTRIBUSI MEDIUM: Beberapa sinyal distribusi aktif. Skor: {distribution_score}/100."
        recommendation = "Kurangi posisi atau hindari penambahan posisi. Smart money mungkin sedang keluar."
    elif risk_level == "high":
        summary = f"🚨 DISTRIBUSI HIGH: Pola distribusi kuat terdeteksi. Skor: {distribution_score}/100."
        recommendation = "JANGAN tambah posisi! Pertimbangkan untuk mulai profit taking atau ketatkan stop loss."
    else:
        summary = f"🚨 DISTRIBUSI EXTREME: Hampir semua indikator menunjukkan distribusi besar. Skor: {distribution_score}/100."
        recommendation = "EXIT segera! Pola ini sering mendahului koreksi tajam. Lindungi modal Anda."

    return DistributionResult(
        is_distributing=is_distributing,
        distribution_score=distribution_score,
        risk_level=risk_level,
        signals=signals,
        mdd_count=mdd_count,
        obv_divergence=obv_divergence,
        volume_dry_up_on_rally=volume_dry_up_on_rally,
        selling_pressure_score=selling_pressure_score,
        summary=summary,
        recommendation=recommendation,
    )
