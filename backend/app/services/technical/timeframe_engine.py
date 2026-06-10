"""
timeframe_engine.py
====================
Multi-Timeframe Analysis Engine untuk AstroCycle.

Filosofi Timeframe Hierarchy:
  Monthly → Weekly → Daily (data yang tersedia saat ini)
  [Future] 1H → 15M (saat koneksi API real-time tersedia)

Karena belum ada koneksi API real-time untuk data intraday (15M/1H),
engine ini bekerja dengan:
1. Data Daily (OHLCV dari database) — sudah tersedia.
2. Simulasi Weekly dari data daily (aggregate per 5 hari kerja).
3. Simulasi Monthly dari data daily (aggregate per 20 hari kerja).
4. Placeholder untuk 1H/15M yang bisa diisi saat API real-time tersedia.

Output hierarki membantu trader memastikan konfirmasi multi-timeframe
sebelum mengeksekusi posisi (top-down analysis).
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from backend.app.services.technical.common import safe_float, score_0_100, clamp
from backend.app.services.technical.indicators import (
    atr, adx, rsi, macd, moving_average, bollinger_position, stochastic, roc
)
from backend.app.services.technical.structure import market_structure


# ─────────────────────────── Timeframe Config ──────────────────────

TIMEFRAME_CONFIGS = {
    "monthly": {
        "label": "Monthly",
        "candles_per_bar": 20,      # 20 hari kerja = 1 bulan
        "min_bars": 6,              # Minimal 6 bulan data
        "description": "Trend besar jangka panjang (Monthly)",
    },
    "weekly": {
        "label": "Weekly",
        "candles_per_bar": 5,       # 5 hari kerja = 1 minggu
        "min_bars": 12,             # Minimal 12 minggu data
        "description": "Trend menengah (Weekly)",
    },
    "daily": {
        "label": "Daily",
        "candles_per_bar": 1,       # 1 candle = 1 hari
        "min_bars": 60,             # Minimal 60 hari data
        "description": "Sinyal entry harian (Daily)",
    },
    "1h": {
        "label": "1-Hour",
        "candles_per_bar": None,    # Butuh data real-time
        "min_bars": None,
        "description": "Konfirmasi entry intraday (1H) — Butuh API real-time",
        "requires_realtime": True,
    },
    "15m": {
        "label": "15-Minute",
        "candles_per_bar": None,    # Butuh data real-time
        "min_bars": None,
        "description": "Trigger entry presisi (15M) — Butuh API real-time",
        "requires_realtime": True,
    },
}


# ─────────────────────────── Aggregation ───────────────────────────

def aggregate_to_timeframe(df: pd.DataFrame, candles_per_bar: int) -> pd.DataFrame:
    """
    Agregasi data OHLCV harian ke timeframe yang lebih tinggi.
    Setiap 'candles_per_bar' candle digabung menjadi 1 candle.

    Parameters
    ----------
    df : pd.DataFrame
        Data OHLCV harian yang sudah di-sort ascending.
    candles_per_bar : int
        Jumlah candle harian per bar output.

    Returns
    -------
    pd.DataFrame
        DataFrame OHLCV yang sudah diagregasi.
    """
    if candles_per_bar <= 1:
        return df.copy()

    df = df.sort_values("date").reset_index(drop=True)
    groups = []

    for i in range(0, len(df), candles_per_bar):
        chunk = df.iloc[i: i + candles_per_bar]
        if len(chunk) == 0:
            continue
        bar = {
            "date": chunk["date"].iloc[-1],
            "open": safe_float(chunk["open"].astype(float).iloc[0]),
            "high": safe_float(chunk["high"].astype(float).max()),
            "low": safe_float(chunk["low"].astype(float).min()),
            "close": safe_float(chunk["close"].astype(float).iloc[-1]),
            "volume": safe_float(chunk["volume"].astype(float).sum()),
        }
        groups.append(bar)

    return pd.DataFrame(groups).reset_index(drop=True)


# ─────────────────────────── Single TF Analysis ────────────────────

def analyze_single_timeframe(df_agg: pd.DataFrame, tf_label: str) -> dict[str, Any]:
    """
    Analisis teknikal untuk satu timeframe dari data yang sudah diagregasi.
    """
    if len(df_agg) < 20:
        return {
            "timeframe": tf_label,
            "status": "insufficient_data",
            "score": 0,
            "trend": "unknown",
            "momentum": "unknown",
            "message": f"Data tidak cukup untuk analisis {tf_label}.",
        }

    close = df_agg["close"].astype(float)
    last_price = safe_float(close.iloc[-1])

    # ── Indicators ──
    rsi_val = rsi(close)
    macd_data = macd(close)
    adx_val = adx(df_agg) if len(df_agg) >= 14 else 20.0
    stoch_val = stochastic(df_agg) if len(df_agg) >= 14 else 50.0
    roc_val = roc(close)

    ma20 = moving_average(close, 20) if len(close) >= 20 else last_price
    ma50 = moving_average(close, 50) if len(close) >= 50 else last_price
    atr_val = atr(df_agg) if len(df_agg) >= 14 else last_price * 0.02

    boll = bollinger_position(close) if len(close) >= 20 else {"position": 0.5}

    # ── Structure ──
    try:
        structure = market_structure(df_agg, atr_val)
        trend_state = structure["trend_state"]
        market_struct = structure["market_structure"]
        breakout_status = structure["breakout_status"]
    except Exception:
        trend_state = "mixed"
        market_struct = "unknown"
        breakout_status = "range"

    # ── Scoring ──
    score_components = []

    # Trend alignment score
    trend_score = 0.0
    if last_price > ma20:
        trend_score += 0.3
    if ma20 > ma50:
        trend_score += 0.3
    if trend_state == "uptrend":
        trend_score += 0.4
    elif trend_state == "range":
        trend_score += 0.15
    score_components.append(("trend", clamp(trend_score)))

    # Momentum score
    momentum_score = 0.0
    if 40 <= rsi_val <= 70:
        momentum_score += 0.35
    if macd_data["histogram"] > 0:
        momentum_score += 0.3
    if macd_data["crossing_up"]:
        momentum_score += 0.15
    if adx_val >= 20:
        momentum_score += 0.2
    score_components.append(("momentum", clamp(momentum_score)))

    # Breakout score
    breakout_score = 0.0
    if breakout_status == "fresh_breakout":
        breakout_score = 1.0
    elif breakout_status == "near_breakout":
        breakout_score = 0.75
    elif breakout_status == "retest_support":
        breakout_score = 0.55
    elif breakout_status == "consolidation":
        breakout_score = 0.4
    elif breakout_status == "breakdown":
        breakout_score = 0.0
    score_components.append(("breakout", breakout_score))

    # Weighted final score
    weights = {"trend": 0.45, "momentum": 0.35, "breakout": 0.20}
    final_score = score_0_100(sum(weights[k] * v for k, v in score_components))

    # ── Bias determination ──
    if final_score >= 70:
        bias = "bullish"
    elif final_score >= 50:
        bias = "neutral_bullish"
    elif final_score >= 35:
        bias = "neutral_bearish"
    else:
        bias = "bearish"

    # ── Momentum label ──
    if macd_data["crossing_up"] and rsi_val > 50:
        momentum_label = "strengthening"
    elif macd_data["histogram"] > 0 and rsi_val >= 50:
        momentum_label = "positive"
    elif macd_data["histogram"] < 0 and rsi_val < 50:
        momentum_label = "weakening"
    else:
        momentum_label = "mixed"

    return {
        "timeframe": tf_label,
        "status": "ok",
        "score": final_score,
        "bias": bias,
        "trend": trend_state,
        "market_structure": market_struct,
        "breakout_status": breakout_status,
        "momentum": momentum_label,
        "indicators": {
            "rsi": round(rsi_val, 2),
            "macd_histogram": round(macd_data["histogram"], 5),
            "macd_crossing_up": macd_data["crossing_up"],
            "adx": round(adx_val, 2),
            "stochastic": round(stoch_val, 2),
            "roc": round(roc_val, 5),
            "bollinger_position": round(boll["position"], 4),
            "ma20": round(ma20, 4),
            "ma50": round(ma50, 4),
        },
        "last_price": round(last_price, 4),
        "atr": round(atr_val, 4),
    }


# ─────────────────────────── Multi-TF Engine ───────────────────────

def multi_timeframe_analysis(df_daily: pd.DataFrame) -> dict[str, Any]:
    """
    Analisis multi-timeframe dari data daily.

    Menghasilkan analisis untuk Monthly, Weekly, dan Daily.
    Timeframe intraday (1H, 15M) ditandai sebagai 'pending_realtime'.

    Parameters
    ----------
    df_daily : pd.DataFrame
        Data OHLCV harian yang sudah di-sort.

    Returns
    -------
    dict
        Dictionary berisi analisis per timeframe dan skor konfirmasi alignment.
    """
    df_sorted = df_daily.sort_values("date").reset_index(drop=True)

    # ── Aggregate ──
    df_monthly = aggregate_to_timeframe(df_sorted, candles_per_bar=20)
    df_weekly = aggregate_to_timeframe(df_sorted, candles_per_bar=5)
    df_daily_clean = df_sorted.copy()

    # ── Analyze per TF ──
    monthly_analysis = analyze_single_timeframe(df_monthly, "monthly")
    weekly_analysis = analyze_single_timeframe(df_weekly, "weekly")
    daily_analysis = analyze_single_timeframe(df_daily_clean, "daily")

    # ── Intraday Placeholder ──
    intraday_placeholder = {
        "status": "pending_realtime",
        "score": None,
        "bias": None,
        "message": (
            "Analisis intraday membutuhkan koneksi API real-time (WebSocket/REST) "
            "untuk data 1H dan 15M. Akan diaktifkan saat integrasi API data tersedia."
        ),
        "action_required": "Daftarkan API key broker atau data provider (Alpaca, Polygon, IDX direct feed).",
    }

    timeframes = {
        "monthly": monthly_analysis,
        "weekly": weekly_analysis,
        "daily": daily_analysis,
        "1h": {**intraday_placeholder, "timeframe": "1h"},
        "15m": {**intraday_placeholder, "timeframe": "15m"},
    }

    # ── Alignment Score ──
    # Seberapa selaras ketiga timeframe yang tersedia?
    available_scores = [
        tf["score"] for tf in [monthly_analysis, weekly_analysis, daily_analysis]
        if tf.get("status") == "ok" and tf.get("score") is not None
    ]
    alignment_score = round(sum(available_scores) / len(available_scores)) if available_scores else 0

    # Alignment bias
    bullish_count = sum(
        1 for tf in [monthly_analysis, weekly_analysis, daily_analysis]
        if tf.get("bias") in ("bullish", "neutral_bullish")
    )
    if bullish_count == 3:
        alignment_bias = "fully_aligned_bullish"
        alignment_label = "Ketiga timeframe selaras BULLISH — sinyal kuat"
    elif bullish_count == 2:
        alignment_bias = "mostly_bullish"
        alignment_label = "2 dari 3 timeframe bullish — konfirmasi cukup"
    elif bullish_count == 1:
        alignment_bias = "mixed"
        alignment_label = "Hanya 1 timeframe bullish — sinyal lemah, wait and see"
    else:
        alignment_bias = "bearish_dominant"
        alignment_label = "Semua timeframe bearish/netral — hindari posisi long"

    # ── Trade Readiness ──
    daily_ok = daily_analysis.get("score", 0) >= 60
    weekly_ok = weekly_analysis.get("score", 0) >= 50
    monthly_ok = monthly_analysis.get("score", 0) >= 45
    trade_ready = daily_ok and weekly_ok and monthly_ok

    return {
        "timeframes": timeframes,
        "alignment": {
            "score": alignment_score,
            "bias": alignment_bias,
            "label": alignment_label,
            "bullish_timeframe_count": bullish_count,
            "trade_ready": trade_ready,
            "trade_readiness_note": (
                "Entry siap: Daily ✅ Weekly ✅ Monthly ✅" if trade_ready
                else "Entry BELUM siap: pastikan Daily + Weekly + Monthly semua konfirmasi bullish."
            ),
        },
        "intraday_availability": {
            "available": False,
            "reason": "API real-time belum terhubung.",
            "how_to_enable": (
                "1. Daftar ke data provider (Alpaca, Polygon.io, atau IDX feed).\n"
                "2. Tambahkan API key ke environment variable (REALTIME_API_KEY).\n"
                "3. Implementasikan WebSocket consumer di backend/app/services/realtime/."
            ),
        },
    }


def get_timeframe_confluence(mta_result: dict[str, Any]) -> dict[str, Any]:
    """
    Mengekstrak poin-poin confluence (persamaan sinyal) dari hasil MTA
    untuk membantu trader mengidentifikasi setup berkualitas tinggi.
    """
    timeframes = mta_result.get("timeframes", {})
    confluence_signals = []
    conflict_signals = []

    available_tfs = {
        k: v for k, v in timeframes.items()
        if isinstance(v, dict) and v.get("status") == "ok"
    }

    breakout_statuses = [v.get("breakout_status") for v in available_tfs.values()]
    trend_states = [v.get("trend") for v in available_tfs.values()]
    momentums = [v.get("momentum") for v in available_tfs.values()]

    if all(s == "uptrend" for s in trend_states if s):
        confluence_signals.append("🟢 Uptrend terkonfirmasi di semua timeframe.")
    elif "uptrend" in trend_states and "downtrend" in trend_states:
        conflict_signals.append("🔴 Konflik tren: Uptrend dan Downtrend bersamaan di timeframe berbeda.")

    if "fresh_breakout" in breakout_statuses or "near_breakout" in breakout_statuses:
        confluence_signals.append("🟢 Breakout signal terdeteksi.")

    if all(m == "strengthening" for m in momentums if m):
        confluence_signals.append("🟢 Momentum menguat di semua timeframe.")
    elif any(m == "weakening" for m in momentums):
        conflict_signals.append("🟡 Momentum melemah di salah satu timeframe.")

    return {
        "confluence_signals": confluence_signals,
        "conflict_signals": conflict_signals,
        "confluence_strength": len(confluence_signals),
        "conflict_count": len(conflict_signals),
        "high_probability_setup": len(confluence_signals) >= 2 and len(conflict_signals) == 0,
    }
