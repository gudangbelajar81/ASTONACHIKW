import pandas as pd

from backend.app.services.technical.common import clamp, safe_float, score_0_100
from backend.app.services.technical.indicators import adx, atr, bollinger_position, ichimoku, macd, moving_average, roc, rsi, stochastic, vwap
from backend.app.services.technical.liquidity_filter import analyze_liquidity
from backend.app.services.technical.relative_strength import relative_strength_profile
from backend.app.services.technical.risk_engine import atr_trade_plan
from backend.app.services.technical.setup_detector import detect_setup
from backend.app.services.technical.structure import market_structure
from backend.app.services.technical.support_resistance import fibonacci_position
from backend.app.services.technical.volume import volume_liquidity


def momentum_layer(df: pd.DataFrame) -> dict:
    close = df["close"].astype(float)
    rsi_value = rsi(close)
    macd_data = macd(close)
    stoch_value = stochastic(df)
    adx_value = adx(df)
    roc_value = roc(close)
    boll = bollinger_position(close)

    rsi_unit = 0.75 if 50 <= rsi_value <= 65 else 0.55 if 40 <= rsi_value < 50 or 65 < rsi_value <= 75 else 0.3
    macd_unit = 0.78 if macd_data["crossing_up"] else 0.68 if macd_data["histogram"] > 0 else 0.35
    adx_unit = clamp((adx_value - 12) / 28)
    boll_unit = 0.72 if 0.45 <= boll["position"] <= 0.85 else 0.45 if boll["position"] < 0.45 else 0.32
    roc_unit = clamp((roc_value + 0.05) / 0.12)
    stochastic_unit = 0.65 if 35 <= stoch_value <= 80 else 0.38
    score = score_0_100(rsi_unit * 0.2 + macd_unit * 0.24 + adx_unit * 0.2 + boll_unit * 0.16 + roc_unit * 0.12 + stochastic_unit * 0.08)
    return {
        "rsi": round(rsi_value, 2),
        "macd": round(macd_data["line"], 4),
        "macd_signal": round(macd_data["signal"], 4),
        "macd_histogram": round(macd_data["histogram"], 4),
        "macd_crossing_up": macd_data["crossing_up"],
        "stochastic": round(stoch_value, 2),
        "adx": round(adx_value, 2),
        "roc": round(roc_value, 4),
        "bollinger_position": round(boll["position"], 4),
        "rsi_score": score_0_100(rsi_unit),
        "macd_score": score_0_100(macd_unit),
        "adx_score": score_0_100(adx_unit),
        "bollinger_score": score_0_100(boll_unit),
        "momentum_score": score,
    }


def trend_layer(df: pd.DataFrame, structure: dict, atr_value: float) -> dict:
    close = df["close"].astype(float)
    last_price = safe_float(close.iloc[-1])
    ma20 = moving_average(close, 20)
    ma50 = moving_average(close, 50)
    ma200 = moving_average(close, 200)
    vwap_value = vwap(df)
    ichi = ichimoku(df)
    fib_position = fibonacci_position(df)
    atr_pct = atr_value / last_price if last_price > 0 else 0.0
    trend_unit = 0.0
    trend_unit += 0.22 if last_price > ma20 else 0
    trend_unit += 0.2 if ma20 > ma50 else 0
    trend_unit += 0.16 if ma50 > ma200 else 0
    trend_unit += 0.12 if last_price > vwap_value else 0
    trend_unit += 0.1 if structure["trend_state"] == "uptrend" else 0.04 if structure["trend_state"] == "mixed" else 0
    trend_unit += 0.08 if structure["breakout_status"] in {"near_breakout", "fresh_breakout"} else 0
    trend_unit += 0.06 if last_price > max(ichi["span_a"], ichi["span_b"]) else 0
    trend_unit += 0.04 if fib_position >= 0.5 else 0
    trend_unit += 0.02 if atr_pct <= 0.06 else 0
    return {
        "ma20": round(ma20, 4),
        "ma50": round(ma50, 4),
        "ma200": round(ma200, 4),
        "vwap": round(vwap_value, 4),
        "fibonacci_position": round(fib_position, 4),
        "ichimoku": {key: round(value, 4) for key, value in ichi.items()},
        "atr_pct": round(atr_pct, 4),
        "trend_score": score_0_100(trend_unit),
    }


def build_technical_profile(df: pd.DataFrame, benchmark_df: pd.DataFrame | None = None, market: str = "id", symbol: str = "") -> dict:
    clean = df.sort_values("date").reset_index(drop=True)
    if len(clean) < 60:
        raise ValueError("Data tidak cukup untuk Technical Engine v2. Minimal 60 candle.")
    close = clean["close"].astype(float)
    last_price = safe_float(close.iloc[-1])
    atr_value = atr(clean)
    structure = market_structure(clean, atr_value)
    trend = trend_layer(clean, structure, atr_value)
    momentum = momentum_layer(clean)
    volume = volume_liquidity(clean)
    relative_strength = relative_strength_profile(clean, benchmark_df)
    # ── Liquidity & Gorengan Analysis ──────────────────────────────
    liquidity_analysis = analyze_liquidity(clean, symbol=symbol)
    risk_plan = atr_trade_plan(
        last_price=last_price,
        atr=atr_value,
        support=structure["nearest_support"],
        resistance=structure["nearest_resistance"],
        market=market,
    )
    setup = detect_setup(structure, momentum, volume, risk_plan)

    volume_score = volume["volume_score"]
    structure_score = structure["score"]
    rs_score = relative_strength["relative_strength_score"]
    risk_score = score_0_100(clamp((risk_plan["risk_reward"] - 0.7) / 2.3))
    technical_score = round(
        trend["trend_score"] * 0.25
        + momentum["momentum_score"] * 0.2
        + volume_score * 0.15
        + structure_score * 0.15
        + rs_score * 0.15
        + risk_score * 0.1
    )

    reasons = []
    risks = []
    if trend["ma20"] > trend["ma50"]:
        reasons.append("Harga berada dalam trend MA20 di atas MA50.")
    if structure["market_structure"] == "higher_high_higher_low":
        reasons.append("Struktur harga masih higher high dan higher low.")
    if volume["volume_confirmation"]:
        reasons.append("Volume mengonfirmasi pergerakan terbaru.")
    if relative_strength["relative_strength_status"] == "outperforming_ihsg":
        reasons.append("Relative strength mengungguli IHSG.")
    if risk_plan["risk_reward"] >= 1.5:
        reasons.append("Risk/reward masih menarik.")
    if structure["breakout_status"] in {"near_breakout", "fresh_breakout"}:
        reasons.append("Harga berada di area breakout atau baru breakout.")

    if last_price >= structure["nearest_resistance"] * 0.98:
        risks.append(f"Harga mendekati resistance {structure['nearest_resistance']}.")
    if risk_plan["stop_loss"] >= last_price:
        risks.append("Stop loss terlalu dekat/kurang sehat terhadap harga terakhir.")
    if volume["volume_dry_up"]:
        risks.append("Volume dry-up, konfirmasi transaksi melemah.")
    if structure["breakout_status"] == "breakdown":
        risks.append("Breakdown terdeteksi, skenario bullish berisiko gagal.")
    risks.append(f"Jika close di bawah {risk_plan['stop_loss']}, skenario bullish invalid.")

    # ── Gorengan risks ke dalam technical_risks ───────────────────
    liquidity_result_dict = liquidity_analysis.to_dict()
    if liquidity_analysis.is_gorengan:
        risks.insert(0, liquidity_analysis.summary)
    for w in liquidity_analysis.warnings[:2]:
        if w.severity in ("EXTREME_WARNING", "WARNING"):
            risks.append(w.message)

    return {
        "technical_score": technical_score,
        "trend_score": trend["trend_score"],
        "momentum_score": momentum["momentum_score"],
        "volume_score": volume_score,
        "relative_strength_score": rs_score,
        "risk_score": risk_score,
        "market_structure_score": structure_score,
        "setup_quality": setup["setup_quality"],
        "setup_type": setup["setup_type"],
        "trend_state": structure["trend_state"],
        "market_structure": structure["market_structure"],
        "breakout_status": structure["breakout_status"],
        "support": structure["nearest_support"],
        "resistance": structure["nearest_resistance"],
        "entry_zone": risk_plan["entry_zone"],
        "stop_loss": risk_plan["stop_loss"],
        "target_1": risk_plan["target_1"],
        "target_2": risk_plan["target_2"],
        "target_3": risk_plan["target_3"],
        "risk_reward": risk_plan["risk_reward"],
        "invalidation": risk_plan["invalidation"],
        "trend": trend,
        "momentum": momentum,
        "volume": volume,
        "relative_strength": relative_strength,
        "structure": structure,
        "setup": setup,
        "atr": round(atr_value, 4),
        "technical_reasons": reasons[:6],
        "technical_risks": risks[:7],
        # ── Liquidity & Gorengan Analysis ────────────────────────
        "liquidity_analysis": liquidity_result_dict,
        "liquidity_grade": liquidity_analysis.liquidity_grade,
        "is_gorengan": liquidity_analysis.is_gorengan,
        "gorengan_risk_level": liquidity_analysis.gorengan_risk_level,
        "liquidity_warnings": [
            {"code": w.code, "severity": w.severity, "message": w.message}
            for w in liquidity_analysis.warnings
        ],
    }
