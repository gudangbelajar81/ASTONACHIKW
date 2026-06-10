"""
DSI Radar Engine — AstroCycle v2
=================================
Menghitung Demand Supply Index (DSI) + VWAP + ATR multi-timeframe
untuk banyak ticker sekaligus, menghasilkan Command Center radar table
seperti SUPREME COMMANDER di TradingView.

Timeframe yang didukung (dari data harian):
  - "1m"  → tidak tersedia (butuh tick data), digantikan short-term momentum
  - "5m"  → tidak tersedia, digantikan 3-hari momentum
  - "15m" → 5-hari momentum
  - "30m" → 10-hari momentum
  - "1h"  → 15-hari momentum
  - "4h"  → 30-hari momentum
  - "D"   → 60-hari momentum

Catatan: karena kita memakai data OHLCV harian (bukan tick/intraday),
TF pendek (1m–1h) diproksikan dari slice candle pendek.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.services.prediction_engine import (
    _safe_float,
    load_price_frame,
    normalize_backend_ticker,
)
from backend.app.services.bandarmology_engine import enrich_ohlcv


# ── Konfigurasi Timeframe ─────────────────────────────────────────────────────
# Pasangan: (label_display, jumlah_candle_harian_untuk_proxying)
TIMEFRAMES: list[tuple[str, int]] = [
    ("1m",  3),
    ("5m",  5),
    ("15m", 10),
    ("30m", 15),
    ("1h",  20),
    ("4h",  30),
    ("D",   60),
]

DSI_LEN = 14



# ── Data Classes ──────────────────────────────────────────────────────────────

@dataclass
class TimeframeSlice:
    label: str
    dsi: float        # 0–100
    close: float
    vwap: float
    dist: float       # % jarak close dari VWAP
    tp: float         # Take Profit = close + ATR×2.5
    sl: float         # Stop Loss  = close - ATR×1.5


@dataclass
class DSIRadarRow:
    symbol: str
    signal: str                          # HAKA | IMBAL | PANTU
    signal_color: str                    # green | blue | yellow
    timeframes: list[TimeframeSlice] = field(default_factory=list)
    confluence_score: float = 0.0       # rata-rata tertimbang DSI semua TF
    dist_15m: float = 0.0
    tp: float = 0.0
    sl: float = 0.0
    last_price: float = 0.0
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "signal": self.signal,
            "signal_color": self.signal_color,
            "confluence_score": round(self.confluence_score, 1),
            "dist": round(self.dist_15m, 2),
            "tp": round(self.tp, 0),
            "sl": round(self.sl, 0),
            "last_price": round(self.last_price, 0),
            "timeframes": [
                {
                    "label": tf.label,
                    "dsi": round(tf.dsi, 1),
                    "dist": round(tf.dist, 2),
                    "tp": round(tf.tp, 0),
                    "sl": round(tf.sl, 0),
                }
                for tf in self.timeframes
            ],
            "error": self.error,
        }


# ── Kalkulasi Inti ────────────────────────────────────────────────────────────

def _compute_dsi(df: pd.DataFrame, period: int = DSI_LEN) -> float:
    """
    DSI = SMA(demand) / (SMA(demand) + SMA(supply)) × 100
    demand = volume jika close naik
    supply = volume jika close turun
    Identik dengan logika f_dsi_val() di Pine Script.
    """
    if len(df) < period + 1:
        return 50.0

    close = df["close"].astype(float)
    vol   = df["volume"].astype(float)
    delta = close.diff()

    demand = vol.where(delta > 0, 0.0)
    supply = vol.where(delta < 0, 0.0)

    sma_demand = demand.rolling(period, min_periods=1).mean().iloc[-1]
    sma_supply = supply.rolling(period, min_periods=1).mean().iloc[-1]
    denom = sma_demand + sma_supply + 1e-9
    return float((sma_demand / denom) * 100)


def _compute_vwap(df: pd.DataFrame) -> float:
    """VWAP = Σ(typical_price × volume) / Σ(volume)"""
    tp  = (df["high"].astype(float) + df["low"].astype(float) + df["close"].astype(float)) / 3
    vol = df["volume"].astype(float)
    total_vol = vol.sum()
    if total_vol <= 0:
        return float(df["close"].iloc[-1])
    return float((tp * vol).sum() / total_vol)


def _compute_atr(df: pd.DataFrame, period: int = 14) -> float:
    high  = df["high"].astype(float)
    low   = df["low"].astype(float)
    close = df["close"].astype(float)
    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low  - close.shift(1)).abs(),
    ], axis=1).max(axis=1)
    atr = float(tr.rolling(min(period, len(tr)), min_periods=1).mean().iloc[-1])
    return atr


def _analyze_timeframe(df: pd.DataFrame, candles: int, label: str) -> TimeframeSlice:
    """
    Ambil slice terakhir sejumlah `candles` baris dari df,
    hitung DSI, VWAP, DIST, TP, SL.
    """
    window = df.tail(max(candles + DSI_LEN, 30)).copy()
    close  = float(window["close"].iloc[-1])
    vwap   = _compute_vwap(window.tail(candles))
    dsi    = _compute_dsi(window)
    dist   = ((close - vwap) / vwap * 100) if vwap > 0 else 0.0
    atr    = _compute_atr(window)
    tp     = close + atr * 2.5
    sl     = close - atr * 1.5
    return TimeframeSlice(
        label=label, dsi=dsi, close=close,
        vwap=vwap, dist=dist, tp=tp, sl=sl,
    )


def _determine_signal(dsi_15m: float, dist_15m: float) -> tuple[str, str]:
    """
    Logika persis seperti f_process() di Pine Script.
    Returns: (signal_label, signal_color)
    """
    if dsi_15m > 60 and dist_15m > 0:
        return "🟢 HAKA", "green"
    if dist_15m < -3:
        return "🔵 IMBAL", "blue"
    return "⚪ PANTU", "yellow"


def _confluence(slices: list[TimeframeSlice]) -> float:
    """
    Confluence score = rata-rata tertimbang DSI semua TF.
    TF yang lebih panjang diberi bobot lebih besar.
    """
    weights = [0.05, 0.08, 0.15, 0.12, 0.20, 0.18, 0.22]
    total_w = sum(weights[:len(slices)])
    if total_w == 0:
        return 50.0
    score = sum(s.dsi * w for s, w in zip(slices, weights)) / total_w
    return round(score, 2)


# ── Analisis satu ticker (dari daily proxy) ───────────────────────────────────

def _build_radar_row_daily(symbol: str, df: pd.DataFrame) -> DSIRadarRow:
    """Bangun RadarRow dari data OHLCV harian (proxy mode)."""
    try:
        enriched = enrich_ohlcv(df).reset_index(drop=True)

        slices: list[TimeframeSlice] = []
        for label, candles in TIMEFRAMES:
            slices.append(_analyze_timeframe(enriched, candles, label))

        tf_15m = slices[2] if len(slices) > 2 else slices[-1]
        signal, color = _determine_signal(tf_15m.dsi, tf_15m.dist)

        return DSIRadarRow(
            symbol=symbol.replace(".JK", ""),
            signal=signal,
            signal_color=color,
            timeframes=slices,
            confluence_score=_confluence(slices),
            dist_15m=tf_15m.dist,
            tp=tf_15m.tp,
            sl=tf_15m.sl,
            last_price=tf_15m.close,
        )
    except Exception as exc:
        clean = symbol.replace(".JK", "")
        return DSIRadarRow(
            symbol=clean, signal="⚪ PANTU", signal_color="yellow",
            confluence_score=50.0, error=str(exc),
        )


async def _build_radar_row_eodhd(
    symbol: str,
    api_key: str,
) -> DSIRadarRow:
    """
    Bangun RadarRow menggunakan data intraday EODHD sungguhan.
    Semua 7 TF dihitung dari data intraday asli.
    """
    from backend.app.services.eodhd_provider import fetch_intraday_ohlcv

    loop = asyncio.get_event_loop()
    clean = symbol.replace(".JK", "")

    try:
        slices: list[TimeframeSlice] = []

        for label, _proxy_candles in TIMEFRAMES:
            try:
                df = await loop.run_in_executor(
                    None,
                    fetch_intraday_ohlcv,
                    clean, label, api_key, "JK", 120,
                )
                if df.empty or len(df) < 5:
                    # Fallback: gunakan slice dari TF sebelumnya atau nilai default
                    slices.append(TimeframeSlice(
                        label=label, dsi=50.0, close=0.0,
                        vwap=0.0, dist=0.0, tp=0.0, sl=0.0,
                    ))
                    continue

                # Konversi ke format standar (datetime → date)
                df_std = df.rename(columns={"datetime": "date"}) if "datetime" in df.columns else df
                # Tambahkan high/low jika tidak ada (EODHD intraday selalu ada)
                slices.append(_analyze_timeframe(df_std, len(df_std), label))

            except Exception:
                slices.append(TimeframeSlice(
                    label=label, dsi=50.0, close=0.0,
                    vwap=0.0, dist=0.0, tp=0.0, sl=0.0,
                ))

        if not slices:
            raise ValueError("Tidak ada slice yang berhasil diambil dari EODHD.")

        # 15m = index 2
        tf_15m = slices[2] if len(slices) > 2 else slices[-1]
        signal, color = _determine_signal(tf_15m.dsi, tf_15m.dist)

        return DSIRadarRow(
            symbol=clean,
            signal=signal,
            signal_color=color,
            timeframes=slices,
            confluence_score=_confluence(slices),
            dist_15m=tf_15m.dist,
            tp=tf_15m.tp,
            sl=tf_15m.sl,
            last_price=tf_15m.close,
        )

    except Exception as exc:
        return DSIRadarRow(
            symbol=clean, signal="⚪ PANTU", signal_color="yellow",
            confluence_score=50.0, error=f"[EODHD] {exc}",
        )


# ── Fungsi publik utama ───────────────────────────────────────────────────────

async def build_dsi_radar(
    session: AsyncSession,
    tickers: list[str],
    market: str = "id",
    eodhd_api_key: str | None = None,
) -> dict[str, Any]:
    """
    Hitung DSI Radar untuk setiap ticker secara paralel.

    Jika EODHD_API_KEY tersedia (dari settings atau parameter),
    akan menggunakan data intraday sungguhan.
    Jika tidak, fallback ke proxy dari data harian.

    Args:
        session:        DB session
        tickers:        List kode saham
        market:         "id" (IDX) atau "us"
        eodhd_api_key:  Override API key (opsional)

    Returns:
        dict berisi list rows DSIRadarRow + metadata
    """
    normalized = [
        normalize_backend_ticker(t.strip(), market)
        for t in tickers if t.strip()
    ]

    # Cek apakah EODHD tersedia
    api_key = (
        eodhd_api_key
        or getattr(settings, "EODHD_API_KEY", "")
    ).strip()
    use_eodhd = bool(api_key) and getattr(settings, "EODHD_ENABLED", True)

    async def _fetch_and_build(symbol: str) -> DSIRadarRow:
        if use_eodhd:
            # Coba EODHD dulu
            row = await _build_radar_row_eodhd(symbol, api_key)
            # Jika berhasil dan harga > 0, pakai EODHD
            if row.last_price > 0:
                return row
            # Fallback ke daily jika EODHD gagal
        try:
            df = await load_price_frame(session, symbol, lookback_days=200)
            if len(df) < 30:
                clean = symbol.replace(".JK", "")
                return DSIRadarRow(
                    symbol=clean, signal="⚪ PANTU", signal_color="yellow",
                    confluence_score=50.0,
                    error="Data kurang dari 30 candle.",
                )
            return _build_radar_row_daily(symbol, df)
        except Exception as exc:
            clean = symbol.replace(".JK", "")
            return DSIRadarRow(
                symbol=clean, signal="⚪ PANTU", signal_color="yellow",
                confluence_score=50.0, error=str(exc),
            )

    tasks = [_fetch_and_build(sym) for sym in normalized]
    rows: list[DSIRadarRow] = await asyncio.gather(*tasks)

    # Sort: HAKA → IMBAL → PANTU, lalu confluence tertinggi
    priority = {"🟢 HAKA": 0, "🔵 IMBAL": 1, "⚪ PANTU": 2}
    rows.sort(key=lambda r: (priority.get(r.signal, 9), -r.confluence_score))

    haka_count  = sum(1 for r in rows if "HAKA"  in r.signal)
    imbal_count = sum(1 for r in rows if "IMBAL" in r.signal)
    pantu_count = sum(1 for r in rows if "PANTU" in r.signal)
    avg_conf    = sum(r.confluence_score for r in rows) / max(len(rows), 1)
    tf_labels   = [tf for tf, _ in TIMEFRAMES]

    # Info sumber data
    if use_eodhd:
        data_source = "🟢 EODHD Intraday (Real-time 1m/5m/15m/30m/1h/4h/D)"
        note = (
            "Data dari EODHD.com. TF 15m dan 30m di-resample dari 5m, "
            "TF 4h di-resample dari 1h. Update otomatis."
        )
    else:
        data_source = "⚠️ Proxy Harian (Yahoo Finance)"
        note = (
            "EODHD API belum dikonfigurasi. Tambahkan EODHD_API_KEY di Settings → "
            "Data Provider untuk mendapatkan data intraday sungguhan."
        )

    return {
        "ticker_count": len(rows),
        "haka_count":   haka_count,
        "imbal_count":  imbal_count,
        "pantu_count":  pantu_count,
        "avg_confluence": round(avg_conf, 1),
        "timeframe_labels": tf_labels,
        "data_source": data_source,
        "rows": [r.to_dict() for r in rows],
        "note": note,
    }
