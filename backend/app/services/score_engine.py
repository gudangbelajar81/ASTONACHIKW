from datetime import date, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.schemas.backtest import BacktestRequest
from backend.app.services.idx_backtest import horizon_to_days, run_idx_backtest
from backend.app.services.prediction_engine import build_idx_recommendation


SCORE_MAX = {
    "technical": 25,
    "volume": 15,
    "relative_strength": 15,
    "bandarmology": 20,
    "risk_reward": 10,
    "macro": 5,
}

SCORE_EXPLANATIONS = {
    "technical": "Trend, posisi harga terhadap MA20/MA50/MA200, momentum, dan area resistance.",
    "volume": "Kenaikan volume 5 hari dibanding rata-rata 20 hari.",
    "relative_strength": "Kinerja saham dibanding benchmark pasar, untuk IDX memakai IHSG.",
    "bandarmology": "Akumulasi/distribusi dari proxy internal atau provider live bila tersedia.",
    "risk_reward": "Kelayakan jarak entry, target, dan stop loss.",
    "macro": "Konteks benchmark/makro sederhana dari kekuatan relatif pasar.",
}


def backtest_verdict(report: dict[str, Any] | None) -> dict[str, Any]:
    if not report:
        return {
            "available": False,
            "win_rate": None,
            "average_return": None,
            "max_drawdown": None,
            "profit_factor": None,
            "expectancy": None,
            "total_trade": 0,
            "beats_ihsg": None,
            "verdict": "Backtest belum tersedia.",
        }
    win_rate = report.get("win_rate")
    profit_factor = report.get("profit_factor")
    total_trade = int(report.get("total_trade") or 0)
    beats_ihsg = report.get("benchmark", {}).get("beats_benchmark")
    if total_trade < 8:
        verdict = "Data backtest belum cukup untuk confidence kuat."
    elif (win_rate or 0) >= 0.58 and (profit_factor or 0) >= 1.2 and beats_ihsg is not False:
        verdict = "Backtest mendukung skor; sinyal layak masuk ranking."
    elif (win_rate or 0) >= 0.5:
        verdict = "Backtest cukup netral; gunakan sebagai watchlist, bukan entry agresif."
    else:
        verdict = "Backtest belum mendukung skor; turunkan prioritas."
    return {
        "available": True,
        "win_rate": win_rate,
        "average_return": report.get("average_return"),
        "max_drawdown": report.get("max_drawdown"),
        "profit_factor": profit_factor,
        "expectancy": report.get("expectancy"),
        "total_trade": total_trade,
        "beats_ihsg": beats_ihsg,
        "verdict": verdict,
    }


def build_score_components(breakdown: dict[str, int]) -> dict[str, dict[str, Any]]:
    return {
        key: {
            "value": int(value),
            "max": SCORE_MAX.get(key, 100),
            "explanation": SCORE_EXPLANATIONS.get(key, "Komponen skor internal."),
        }
        for key, value in breakdown.items()
    }


async def build_prediction_score(
    session: AsyncSession,
    ticker: str,
    horizon: str = "weekly",
    market: str = "id",
    backtest_start: date | None = None,
    backtest_end: date | None = None,
) -> dict[str, Any]:
    recommendation = await build_idx_recommendation(session, ticker, horizon=horizon, market=market)
    end = backtest_end or date.today()
    start = backtest_start or (end - timedelta(days=540))
    backtest = None
    try:
        backtest = await run_idx_backtest(
            session,
            BacktestRequest(
                ticker=recommendation["symbol"],
                start_date=start,
                end_date=end,
                horizon=f"{horizon_to_days(horizon)}d",
                rule_entry="score_gt_70",
                rule_exit="target_stop_or_horizon",
                stop_loss=0.03,
                target_profit=0.06,
            ),
        )
    except Exception:
        backtest = None

    entry = recommendation["entry_zone"]
    invalidation = f"Skenario batal jika harga menembus stop loss {recommendation['stop_loss']}."
    scenario = (
        f"Pantau entry {entry[0]}-{entry[1]}, target pertama {recommendation['target_1']}, "
        f"target kedua {recommendation['target_2']}, risk/reward {recommendation['risk_reward']}x."
    )
    return {
        "symbol": recommendation["symbol"],
        "market": recommendation["market"],
        "horizon": recommendation["horizon"],
        "final_score": recommendation["final_score"],
        "signal": recommendation["signal"],
        "confidence": recommendation["confidence"],
        "last_price": recommendation["last_price"],
        "entry_zone": recommendation["entry_zone"],
        "target_1": recommendation["target_1"],
        "target_2": recommendation["target_2"],
        "stop_loss": recommendation["stop_loss"],
        "risk_reward": recommendation["risk_reward"],
        "score_components": build_score_components(recommendation["score_breakdown"]),
        "main_reasons": recommendation["main_reasons"],
        "main_risks": recommendation["main_risks"],
        "invalidation": invalidation,
        "scenario": scenario,
        "backtest_confidence": backtest_verdict(backtest),
        "data_quality": recommendation["data_quality"],
    }
