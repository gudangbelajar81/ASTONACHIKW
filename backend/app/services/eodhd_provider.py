"""
EODHD Intraday Provider — AstroCycle v2
=========================================
Mengambil data OHLCV intraday dari EODHD.com API.

Endpoint EODHD yang didukung:
  - Intraday:  https://eodhd.com/api/intraday/{symbol}.{exchange}
               interval: 1m, 5m, 1h
  - EOD daily: https://eodhd.com/api/eod/{symbol}.{exchange}

Resample otomatis:
  1m  → langsung
  5m  → langsung
  15m → resample dari 5m (3 candle)
  30m → resample dari 5m (6 candle)
  1h  → langsung
  4h  → resample dari 1h (4 candle)
  D   → resample dari 1h atau EOD
"""

from __future__ import annotations

import time
import urllib.request
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

import pandas as pd

from backend.app.core.config import settings


# ── Base URL ────────────────────────────────────────────────────────────────
EODHD_BASE = "https://eodhd.com/api"

# EODHD interval yang tersedia secara native
EODHD_NATIVE_INTERVALS = {"1m", "5m", "1h"}

# Mapping TF → (native_interval, resample_rule)
# resample_rule = None jika native, atau pandas offset string
TF_MAP: dict[str, tuple[str, Optional[str]]] = {
    "1m":  ("1m",  None),
    "5m":  ("5m",  None),
    "15m": ("5m",  "15min"),
    "30m": ("5m",  "30min"),
    "1h":  ("1h",  None),
    "4h":  ("1h",  "4h"),
    "D":   ("1h",  "D"),
}

# Cache sederhana di memory: {(symbol, interval): (timestamp, df)}
_CACHE: dict[tuple[str, str], tuple[float, pd.DataFrame]] = {}
CACHE_TTL_SECONDS = 300   # 5 menit


@dataclass
class EODHDConfig:
    api_key: str
    exchange: str = "JK"   # JK = IDX Indonesia


def _get_api_key() -> str:
    """Ambil EODHD API key dari config/settings."""
    key = getattr(settings, "EODHD_API_KEY", "")
    if not key:
        raise ValueError(
            "EODHD_API_KEY belum dikonfigurasi. "
            "Tambahkan di file .env: EODHD_API_KEY=your_key_here"
        )
    return key.strip()


def _eodhd_symbol(ticker: str, exchange: str = "JK") -> str:
    """
    Konversi ticker ke format EODHD.
    Contoh: BBCA → BBCA.JK
            BBCA.JK → BBCA.JK (tidak berubah)
    """
    clean = ticker.replace(".JK", "").replace(".IDX", "").upper()
    return f"{clean}.{exchange}"


def _fetch_url(url: str, timeout: int = 15) -> list[dict]:
    """Fetch JSON dari URL EODHD."""
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "AstroCycle/2.0 (+https://astrocycle.app)"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _fetch_intraday_raw(
    symbol: str,
    interval: str,
    api_key: str,
    lookback_hours: int = 72,
) -> pd.DataFrame:
    """
    Ambil data intraday dari EODHD.
    Returns DataFrame dengan kolom: datetime, open, high, low, close, volume
    """
    cache_key = (symbol, interval)
    now = time.time()

    # Cek cache
    if cache_key in _CACHE:
        cached_ts, cached_df = _CACHE[cache_key]
        if now - cached_ts < CACHE_TTL_SECONDS:
            return cached_df

    # Hitung from/to unix timestamp
    to_ts   = int(now)
    from_ts = int(now - lookback_hours * 3600)

    url = (
        f"{EODHD_BASE}/intraday/{symbol}"
        f"?interval={interval}"
        f"&api_token={api_key}"
        f"&from={from_ts}&to={to_ts}"
        f"&fmt=json"
    )

    raw = _fetch_url(url)
    if not raw:
        return pd.DataFrame()

    df = pd.DataFrame(raw)

    # Normalisasi kolom
    if "timestamp" in df.columns:
        df["datetime"] = pd.to_datetime(df["timestamp"], unit="s", utc=True)
    elif "datetime" in df.columns:
        df["datetime"] = pd.to_datetime(df["datetime"], utc=True)
    else:
        return pd.DataFrame()

    # Rename kolom ke lowercase standar
    rename_map = {
        "open": "open", "high": "high", "low": "low",
        "close": "close", "volume": "volume",
    }
    for src, dst in rename_map.items():
        if src in df.columns:
            df[dst] = pd.to_numeric(df[src], errors="coerce")

    df = df[["datetime", "open", "high", "low", "close", "volume"]].dropna()
    df = df.sort_values("datetime").reset_index(drop=True)

    # Simpan ke cache
    _CACHE[cache_key] = (now, df)
    return df


def _resample_ohlcv(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    """
    Resample DataFrame intraday ke TF yang lebih besar.
    rule: pandas offset string, misal '15min', '30min', '4h', 'D'
    """
    if df.empty:
        return df

    df = df.set_index("datetime")
    resampled = df.resample(rule).agg({
        "open":   "first",
        "high":   "max",
        "low":    "min",
        "close":  "last",
        "volume": "sum",
    }).dropna().reset_index()

    return resampled


def fetch_intraday_ohlcv(
    ticker: str,
    timeframe: str,
    api_key: Optional[str] = None,
    exchange: str = "JK",
    lookback_hours: int = 72,
) -> pd.DataFrame:
    """
    Ambil OHLCV intraday untuk satu ticker dan timeframe tertentu.

    Args:
        ticker:        Kode saham, misal "BBCA" atau "BBCA.JK"
        timeframe:     "1m" | "5m" | "15m" | "30m" | "1h" | "4h" | "D"
        api_key:       EODHD API key (opsional, ambil dari settings jika kosong)
        exchange:      Exchange code EODHD, default "JK" untuk IDX
        lookback_hours: Berapa jam ke belakang

    Returns:
        DataFrame dengan kolom: datetime, open, high, low, close, volume
        Diurutkan ascending berdasarkan datetime.
    """
    key  = api_key or _get_api_key()
    sym  = _eodhd_symbol(ticker, exchange)
    tf   = timeframe.lower()

    if tf not in TF_MAP:
        raise ValueError(f"Timeframe '{timeframe}' tidak didukung. Pilihan: {list(TF_MAP.keys())}")

    native_interval, resample_rule = TF_MAP[tf]

    # Sesuaikan lookback agar cukup candle
    if tf in {"4h", "D"}:
        lookback_hours = max(lookback_hours, 168)   # 7 hari untuk TF besar

    df = _fetch_intraday_raw(sym, native_interval, key, lookback_hours)

    if df.empty:
        return df

    if resample_rule:
        df = _resample_ohlcv(df, resample_rule)

    return df


async def fetch_multi_tf_ohlcv(
    ticker: str,
    timeframes: list[str],
    api_key: Optional[str] = None,
    exchange: str = "JK",
) -> dict[str, pd.DataFrame]:
    """
    Ambil OHLCV intraday untuk banyak timeframe sekaligus (efisien, reuse cache).

    Returns:
        Dict {timeframe: DataFrame}
    """
    import asyncio

    loop = asyncio.get_event_loop()
    results: dict[str, pd.DataFrame] = {}

    def _fetch_one(tf: str) -> tuple[str, pd.DataFrame]:
        try:
            df = fetch_intraday_ohlcv(ticker, tf, api_key, exchange)
            return tf, df
        except Exception:
            return tf, pd.DataFrame()

    tasks = [loop.run_in_executor(None, _fetch_one, tf) for tf in timeframes]
    fetched = await asyncio.gather(*tasks)

    for tf, df in fetched:
        results[tf] = df

    return results


def test_eodhd_connection(api_key: str) -> dict:
    """
    Uji koneksi ke EODHD API.
    Returns: {"status": "live"|"dead", "detail": str}
    """
    try:
        # Test dengan BBCA (saham paling likuid IDX)
        url = (
            f"{EODHD_BASE}/intraday/BBCA.JK"
            f"?interval=1h"
            f"&api_token={api_key}"
            f"&fmt=json"
            f"&limit=5"
        )
        raw = _fetch_url(url, timeout=10)
        if raw and len(raw) > 0:
            return {
                "status": "live",
                "detail": f"Koneksi berhasil. {len(raw)} candle diterima.",
            }
        return {"status": "dead", "detail": "Respons kosong dari EODHD."}
    except Exception as exc:
        return {"status": "dead", "detail": str(exc)}
