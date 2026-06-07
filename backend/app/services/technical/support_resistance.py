import pandas as pd

from backend.app.services.technical.common import safe_float


def nearest_levels(df: pd.DataFrame, lookback: int = 60) -> dict:
    recent = df.tail(lookback)
    close = safe_float(recent["close"].iloc[-1])
    highs = recent["high"].astype(float)
    lows = recent["low"].astype(float)
    resistance = safe_float(highs.tail(30).max(), close * 1.04)
    support = safe_float(lows.tail(30).min(), close * 0.96)
    range_high = safe_float(highs.max(), resistance)
    range_low = safe_float(lows.min(), support)
    return {
        "nearest_resistance": round(resistance, 4),
        "nearest_support": round(support, 4),
        "range_high": round(range_high, 4),
        "range_low": round(range_low, 4),
    }


def fibonacci_position(df: pd.DataFrame, lookback: int = 60) -> float:
    recent = df.tail(lookback)
    close = safe_float(recent["close"].iloc[-1])
    high = safe_float(recent["high"].astype(float).max(), close)
    low = safe_float(recent["low"].astype(float).min(), close)
    return (close - low) / max(high - low, 0.000001)
