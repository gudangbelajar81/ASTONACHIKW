from backend.app.services.technical.common import safe_float


def atr_trade_plan(
    *,
    last_price: float,
    atr: float,
    support: float,
    resistance: float,
    market: str = "id",
) -> dict:
    entry_low = last_price - atr * 0.3
    entry_high = last_price + atr * 0.3
    stop_atr = last_price - atr * 1.5
    stop_loss = min(support, stop_atr) if support < last_price else stop_atr
    risk = max(entry_high - stop_loss, 0.01)
    target_1 = max(resistance, entry_high + risk * 1.2)
    target_2 = entry_high + risk * 2
    target_3 = entry_high + risk * 3
    risk_reward = (target_2 - entry_high) / risk if risk > 0 else 0.0
    return {
        "entry_zone": [round(entry_low, 2), round(entry_high, 2)],
        "stop_loss": round(stop_loss, 2),
        "target_1": round(target_1, 2),
        "target_2": round(target_2, 2),
        "target_3": round(target_3, 2),
        "risk_reward": round(risk_reward, 2),
        "invalidation": f"close below {round(stop_loss, 2)}",
        "risk_per_share": round(safe_float(risk), 4),
    }
