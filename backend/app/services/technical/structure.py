import pandas as pd

from backend.app.services.technical.common import safe_float, score_0_100
from backend.app.services.technical.support_resistance import nearest_levels


def swing_points(df: pd.DataFrame, window: int = 3) -> tuple[list[tuple[int, float]], list[tuple[int, float]]]:
    highs: list[tuple[int, float]] = []
    lows: list[tuple[int, float]] = []
    high = df["high"].astype(float).reset_index(drop=True)
    low = df["low"].astype(float).reset_index(drop=True)
    for index in range(window, len(df) - window):
        h = high.iloc[index]
        l = low.iloc[index]
        if h >= high.iloc[index - window : index + window + 1].max():
            highs.append((index, safe_float(h)))
        if l <= low.iloc[index - window : index + window + 1].min():
            lows.append((index, safe_float(l)))
    return highs[-4:], lows[-4:]


def market_structure(df: pd.DataFrame, atr_value: float) -> dict:
    levels = nearest_levels(df)
    close = safe_float(df["close"].iloc[-1])
    highs, lows = swing_points(df.tail(90).reset_index(drop=True))
    high_state = "flat_high"
    low_state = "flat_low"
    if len(highs) >= 2:
        high_state = "higher_high" if highs[-1][1] > highs[-2][1] else "lower_high"
    if len(lows) >= 2:
        low_state = "higher_low" if lows[-1][1] > lows[-2][1] else "lower_low"

    if high_state == "higher_high" and low_state == "higher_low":
        structure = "higher_high_higher_low"
        trend_state = "uptrend"
        structure_score = 0.86
    elif high_state == "lower_high" and low_state == "lower_low":
        structure = "lower_high_lower_low"
        trend_state = "downtrend"
        structure_score = 0.22
    elif high_state == "lower_high" and low_state == "higher_low":
        structure = "consolidation"
        trend_state = "range"
        structure_score = 0.52
    else:
        structure = f"{high_state}_{low_state}"
        trend_state = "mixed"
        structure_score = 0.48

    resistance = safe_float(levels["nearest_resistance"], close)
    support = safe_float(levels["nearest_support"], close)
    distance_to_resistance = close / resistance - 1 if resistance > 0 else 0
    distance_to_support = close / support - 1 if support > 0 else 0
    atr_pct = atr_value / close if close > 0 else 0
    range_width = (safe_float(levels["range_high"]) - safe_float(levels["range_low"])) / close if close > 0 else 0
    consolidation = range_width < max(atr_pct * 5, 0.08)

    if close > resistance:
        breakout_status = "fresh_breakout"
    elif distance_to_resistance >= -max(atr_pct * 1.2, 0.03):
        breakout_status = "near_breakout"
    elif close < support:
        breakout_status = "breakdown"
    elif distance_to_support <= max(atr_pct * 1.4, 0.04):
        breakout_status = "retest_support"
    elif consolidation:
        breakout_status = "consolidation"
    else:
        breakout_status = "range"

    if breakout_status in {"fresh_breakout", "near_breakout"}:
        structure_score += 0.08
    if breakout_status == "breakdown":
        structure_score -= 0.18

    return {
        "market_structure": structure,
        "trend_state": trend_state,
        "breakout_status": breakout_status,
        "nearest_resistance": round(resistance, 4),
        "nearest_support": round(support, 4),
        "range": {"high": levels["range_high"], "low": levels["range_low"], "width_pct": round(range_width, 4)},
        "consolidation": consolidation,
        "score": score_0_100(structure_score),
    }
