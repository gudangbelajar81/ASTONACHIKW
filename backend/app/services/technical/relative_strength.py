import pandas as pd

from backend.app.services.technical.common import clamp, safe_float, score_0_100


def pct_change(close: pd.Series, days: int) -> float:
    if len(close) <= days:
        return 0.0
    base = safe_float(close.iloc[-days - 1])
    latest = safe_float(close.iloc[-1])
    return latest / base - 1 if base > 0 else 0.0


def relative_strength_profile(stock_df: pd.DataFrame, benchmark_df: pd.DataFrame | None) -> dict:
    stock_close = stock_df["close"].astype(float)
    if benchmark_df is None or len(benchmark_df) < 30:
        return {
            "rs_vs_ihsg_20d": 0.0,
            "rs_vs_ihsg_60d": 0.0,
            "rs_vs_ihsg_120d": 0.0,
            "relative_strength_status": "benchmark_unavailable",
            "relative_strength_score": 50,
        }

    benchmark_close = benchmark_df["close"].astype(float)
    rs20 = pct_change(stock_close, 20) - pct_change(benchmark_close, 20)
    rs60 = pct_change(stock_close, 60) - pct_change(benchmark_close, 60)
    rs120 = pct_change(stock_close, 120) - pct_change(benchmark_close, 120)
    blended = rs20 * 0.5 + rs60 * 0.32 + rs120 * 0.18
    if rs20 > 0 and rs60 > 0:
        status = "outperforming_ihsg"
    elif rs20 > 0:
        status = "short_term_outperform"
    elif rs20 < -0.04 and rs60 < 0:
        status = "underperforming_ihsg"
    else:
        status = "neutral_vs_ihsg"
    return {
        "rs_vs_ihsg_20d": round(rs20, 4),
        "rs_vs_ihsg_60d": round(rs60, 4),
        "rs_vs_ihsg_120d": round(rs120, 4),
        "relative_strength_status": status,
        "relative_strength_score": score_0_100(clamp((blended + 0.08) / 0.16)),
    }
