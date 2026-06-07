from backend.app.services.technical.common import score_0_100


def detect_setup(structure: dict, momentum: dict, volume: dict, risk_plan: dict) -> dict:
    breakout = structure["breakout_status"]
    trend = structure["trend_state"]
    rsi = momentum.get("rsi", 50)
    macd_positive = momentum.get("macd_histogram", 0) > 0
    volume_confirmed = volume.get("volume_confirmation", False)
    rr = risk_plan.get("risk_reward", 0)

    setup_type = "avoid"
    quality = 0.35
    if breakout == "near_breakout" and trend in {"uptrend", "mixed"}:
        setup_type = "breakout_candidate"
        quality = 0.62
    if breakout == "fresh_breakout" and volume_confirmed:
        setup_type = "fresh_breakout"
        quality = 0.74
    if breakout == "retest_support" and trend == "uptrend":
        setup_type = "pullback_to_support"
        quality = 0.72
    if trend == "uptrend" and macd_positive and 45 <= rsi <= 70:
        setup_type = "trend_continuation"
        quality = max(quality, 0.7)
    if trend == "downtrend" and rsi < 35:
        setup_type = "reversal_candidate"
        quality = max(quality, 0.46)
    if breakout == "breakdown" or volume.get("volume_dry_up"):
        setup_type = "distribution_risk"
        quality = min(quality, 0.32)
    if rr >= 1.5:
        quality += 0.08
    if volume_confirmed:
        quality += 0.07

    return {
        "setup_type": setup_type,
        "breakout_level": structure["nearest_resistance"],
        "confirmation_level": round(structure["nearest_resistance"] * 1.005, 2),
        "pullback_zone": [structure["nearest_support"], round(structure["nearest_support"] * 1.02, 2)],
        "setup_quality": score_0_100(quality),
    }
