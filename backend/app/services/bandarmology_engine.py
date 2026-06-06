from datetime import date, timedelta

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.services.prediction_engine import clamp, load_price_frame


def enrich_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    enriched = df.copy().sort_values("date").reset_index(drop=True)
    close = enriched["close"].astype(float)
    enriched["ma20"] = close.rolling(20, min_periods=5).mean()
    enriched["ma50"] = close.rolling(50, min_periods=10).mean()
    enriched["ma200"] = close.rolling(200, min_periods=30).mean()
    return enriched


def calculate_obv(df: pd.DataFrame) -> pd.Series:
    close = df["close"].astype(float)
    volume = df["volume"].astype(float)
    direction = close.diff().fillna(0).apply(lambda value: 1 if value > 0 else -1 if value < 0 else 0)
    return (direction * volume).cumsum()


def calculate_money_flow_score(df: pd.DataFrame) -> float:
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    close = df["close"].astype(float)
    volume = df["volume"].astype(float)
    typical = (high + low + close) / 3
    raw_flow = typical * volume
    positive = raw_flow.where(typical.diff().fillna(0) > 0, 0).tail(14).sum()
    negative = raw_flow.where(typical.diff().fillna(0) < 0, 0).tail(14).sum()
    if positive + negative <= 0:
        return 0.0
    money_flow_index = 100 - (100 / (1 + positive / max(abs(negative), 1)))
    return clamp((float(money_flow_index) - 50) / 50)


def calculate_accumulation_distribution(df: pd.DataFrame) -> pd.Series:
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    close = df["close"].astype(float)
    volume = df["volume"].astype(float)
    money_flow_multiplier = ((close - low) - (high - close)) / (high - low).replace(0, 1)
    return (money_flow_multiplier.fillna(0) * volume).cumsum()


def build_bandarmology(df: pd.DataFrame, ticker: str) -> dict:
    if df.empty:
        raise ValueError("Data OHLCV kosong.")

    enriched = enrich_ohlcv(df)
    latest = enriched.iloc[-1]
    volume = enriched["volume"].astype(float)
    close = enriched["close"].astype(float)
    obv = calculate_obv(enriched)
    ad_line = calculate_accumulation_distribution(enriched)

    avg_volume_20 = float(volume.rolling(20, min_periods=5).mean().iloc[-1] or 0)
    volume_spike = float(volume.iloc[-1] / avg_volume_20) if avg_volume_20 > 0 else 0.0
    recent_close_position = float(((latest.close - latest.low) / max(latest.high - latest.low, 0.01)) * 2 - 1)
    obv_slope = float(obv.tail(10).iloc[-1] - obv.tail(10).iloc[0]) if len(obv) >= 10 else 0.0
    ad_slope = float(ad_line.tail(10).iloc[-1] - ad_line.tail(10).iloc[0]) if len(ad_line) >= 10 else 0.0
    volume_pressure = clamp((volume_spike - 1) / 2)
    money_flow_score = calculate_money_flow_score(enriched)
    accumulation_score = clamp(
        (1 if ad_slope > 0 else -1 if ad_slope < 0 else 0) * 0.45
        + (1 if obv_slope > 0 else -1 if obv_slope < 0 else 0) * 0.35
        + recent_close_position * 0.2
    )
    distribution_score = clamp(-accumulation_score)
    smart_money_score = clamp(
        accumulation_score * 0.45
        + money_flow_score * 0.25
        + volume_pressure * 0.2
        + recent_close_position * 0.1
    )
    support = float(enriched["low"].tail(30).min())
    resistance = float(enriched["high"].tail(30).max())
    obv_trend = "naik" if obv_slope > 0 else "turun" if obv_slope < 0 else "netral"

    notes = []
    if volume_spike >= 1.8 and latest.close >= latest.open:
        notes.append("Volume spike muncul saat candle hijau, indikasi akumulasi proxy.")
    if volume_spike >= 1.8 and latest.close < latest.open:
        notes.append("Volume spike muncul saat candle merah, waspadai distribusi.")
    if obv_trend == "naik":
        notes.append("OBV cenderung naik, volume mendukung kenaikan harga.")
    if money_flow_score > 0.25:
        notes.append("Money flow proxy positif.")
    if not notes:
        notes.append("Belum ada sinyal bandar proxy yang dominan.")

    if smart_money_score >= 0.35:
        verdict = "akumulasi"
    elif smart_money_score <= -0.35:
        verdict = "distribusi"
    else:
        verdict = "netral"

    return {
        "ticker": ticker.upper(),
        "as_of_date": str(latest.date),
        "smart_money_score": smart_money_score,
        "accumulation_score": accumulation_score,
        "distribution_score": distribution_score,
        "volume_spike": volume_spike,
        "obv_trend": obv_trend,
        "money_flow_score": money_flow_score,
        "support": round(support, 2),
        "resistance": round(resistance, 2),
        "verdict": verdict,
        "notes": notes,
    }


async def build_ohlcv_report(session: AsyncSession, ticker: str, lookback_days: int = 260) -> dict:
    df = await load_price_frame(session, ticker.upper(), max(lookback_days, 260))
    enriched = enrich_ohlcv(df).tail(lookback_days)
    points = []
    for row in enriched.itertuples(index=False):
        points.append(
            {
                "date": row.date.isoformat() if hasattr(row.date, "isoformat") else str(row.date),
                "open": float(row.open),
                "high": float(row.high),
                "low": float(row.low),
                "close": float(row.close),
                "volume": float(row.volume or 0),
                "ma20": None if pd.isna(row.ma20) else float(row.ma20),
                "ma50": None if pd.isna(row.ma50) else float(row.ma50),
                "ma200": None if pd.isna(row.ma200) else float(row.ma200),
            }
        )

    return {
        "ticker": ticker.upper(),
        "points": points,
        "bandarmology": build_bandarmology(enriched, ticker),
    }
