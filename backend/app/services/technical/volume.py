import pandas as pd

from backend.app.services.technical.common import clamp, safe_float, score_0_100


def volume_liquidity(df: pd.DataFrame) -> dict:
    close = df["close"].astype(float)
    volume = df["volume"].astype(float)
    avg_volume_20 = safe_float(volume.tail(20).mean())
    avg_value_20 = avg_volume_20 * safe_float(close.tail(20).mean())
    latest_volume = safe_float(volume.iloc[-1])
    latest_value = latest_volume * safe_float(close.iloc[-1])
    volume_vs_20d = latest_volume / avg_volume_20 if avg_volume_20 > 0 else 0.0
    volume_spike = volume_vs_20d >= 1.5
    volume_dry_up = volume_vs_20d <= 0.65
    volume_confirmation = volume_vs_20d >= 1.0 and safe_float(close.iloc[-1]) >= safe_float(close.iloc[-2], close.iloc[-1])
    liquidity_unit = clamp(avg_value_20 / 10_000_000_000)
    volume_unit = clamp((volume_vs_20d - 0.65) / 1.35)
    score = score_0_100(liquidity_unit * 0.55 + volume_unit * 0.45)
    return {
        "volume_score": score,
        "liquidity_score": score_0_100(liquidity_unit),
        "avg_volume_20d": round(avg_volume_20, 2),
        "avg_value_20d": round(avg_value_20, 2),
        "value_traded": round(latest_value, 2),
        "volume_vs_20d_avg": round(volume_vs_20d, 2),
        "volume_spike": volume_spike,
        "volume_dry_up": volume_dry_up,
        "volume_confirmation": volume_confirmation,
    }
