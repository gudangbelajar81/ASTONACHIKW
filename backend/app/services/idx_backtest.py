from datetime import date, timedelta
from typing import Any

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.services.bandarmology_engine import build_bandarmology, enrich_ohlcv
from backend.app.services.prediction_engine import (
    build_expanded_technical_context,
    _max_drawdown,
    _round_price,
    _safe_float,
    build_idx_recommendation,
    clamp,
    load_price_frame,
    normalize_backend_ticker,
)
from backend.app.services.technical import build_technical_profile
from backend.app.services.technical.liquidity_filter import analyze_liquidity
from backend.app.services.news_sentiment_engine import (
    fetch_news_sentiment,
    apply_news_sentiment_weighting,
)


# ── IDX Universe (~120 saham lintas sektor) ──────────────────────────────────
IDX_UNIVERSE = [
    # Perbankan & Keuangan
    "BBCA", "BBRI", "BMRI", "BBNI", "BRIS", "BTPS", "BBTN", "NISP", "BNGA", "BJBR",
    "BNLI", "MEGA", "BDMN", "PNBN", "BJTM", "AGRO",
    # Telekomunikasi & Teknologi
    "TLKM", "EXCL", "ISAT", "TOWR", "GOTO", "DMMX", "EMTK", "MTEL",
    # Energi & Tambang
    "ADRO", "PTBA", "ITMG", "HRUM", "BUMI", "INCO", "ANTM", "MDKA", "MEDC",
    "PGAS", "ELSA", "AKRA", "RATU", "MBAP", "BSSR",
    # Konsumer & Ritel
    "UNVR", "ICBP", "INDF", "CPIN", "JPFA", "AMRT", "MAPI", "ACES", "LPPF",
    "MYOR", "SIDO", "ULTJ", "DLTA", "AISA", "HMSP", "GGRM", "WIIM",
    # Properti & Konstruksi
    "BSDE", "SMRA", "CTRA", "ASRI", "PWON", "LPKR", "DMAS", "WIKA", "WSKT",
    "ADHI", "PTPP", "SSIA",
    # Infrastruktur & Utilitas
    "JSMR", "TLKM", "PGAS", "KRAS", "WTON", "SMGR", "INTP",
    # Otomotif & Manufaktur
    "ASII", "UNTR", "AUTO", "SMSM", "INDS", "GJTL", "GDYR",
    # Kesehatan & Farmasi
    "KLBF", "SIDO", "KAEF", "MIKA", "HEAL", "PRDA", "DVLA", "TSPC",
    # Industri Dasar
    "INKP", "TKIM", "ISSP", "KRAS", "GDST", "ALMI",
    # Media & Hiburan
    "SCMA", "MNCN", "FILM",
    # Asuransi & Multifinance
    "ASEI", "MREI", "BFIN", "ADMF", "BNII",
]


def horizon_to_days(value: str) -> int:
    normalized = value.strip().lower()
    if normalized in {"1d", "daily", "harian"}:
        return 1
    if normalized in {"20d", "monthly", "bulanan"}:
        return 20
    return 5


def horizon_label(value: str) -> str:
    days = horizon_to_days(value)
    if days == 1:
        return "daily"
    if days == 20:
        return "monthly"
    return "weekly"


def normalize_pct(value: float) -> float:
    return value / 100 if value > 1 else value


def compute_historical_score(window: pd.DataFrame, benchmark_window: pd.DataFrame | None = None) -> tuple[int, dict[str, int], dict[str, Any]]:
    if len(window) < 60:
        return 0, {}, {"reason": "Data kurang dari 60 candle."}

    enriched = enrich_ohlcv(window).reset_index(drop=True)
    latest = enriched.iloc[-1]
    close = enriched["close"].astype(float)
    volume = enriched["volume"].astype(float)
    latest_close = _safe_float(latest.close)
    ma20 = _safe_float(latest.ma20, latest_close)
    ma50 = _safe_float(latest.ma50, latest_close)
    ma200 = _safe_float(latest.ma200, latest_close)
    volume_5 = _safe_float(volume.tail(5).mean())
    volume_20 = _safe_float(volume.tail(20).mean())
    value_20 = volume_20 * _safe_float(close.tail(20).mean(), latest_close)
    volume_ratio = volume_5 / volume_20 if volume_20 > 0 else 1.0
    return_20 = latest_close / _safe_float(close.iloc[-21], latest_close) - 1 if len(close) > 21 else 0.0
    try:
        technical_profile = build_technical_profile(enriched, benchmark_window)
    except Exception:
        technical_profile = None
    technical_context = (
        technical_profile
        if technical_profile
        else build_expanded_technical_context(enriched, latest_close, ma20, ma50, ma200)
    )

    relative_strength = 0.0
    if benchmark_window is not None and len(benchmark_window) > 21:
        benchmark_close = benchmark_window["close"].astype(float)
        benchmark_return = _safe_float(benchmark_close.iloc[-1]) / _safe_float(benchmark_close.iloc[-21], 1) - 1
        relative_strength = return_20 - benchmark_return

    try:
        bandarmology = build_bandarmology(enriched, str(window.iloc[-1].get("symbol", "")))
    except Exception:
        bandarmology = {"verdict": "netral", "smart_money_score": 0.0}

    trend_score = round((technical_profile["trend_score"] / 100 * 20) if technical_profile else technical_context["score"] * 20)
    momentum_score = round((technical_profile["momentum_score"] / 100 * 15) if technical_profile else clamp((return_20 + 0.04) / 0.12, 0, 1) * 15)
    liquidity_unit = min(1.0, value_20 / 5_000_000_000)
    volume_score = round((technical_profile["volume_score"] / 100 * 15) if technical_profile else (clamp((volume_ratio - 0.8) / 0.8, 0, 1) * 0.65 + liquidity_unit * 0.35) * 15)
    rs_score = round((technical_profile["relative_strength_score"] / 100 * 10) if technical_profile else min(10, max(0, round((relative_strength + 0.04) / 0.12 * 10))))
    smart_money = _safe_float(bandarmology.get("smart_money_score"))
    broker_component = 5
    foreign_component = 3
    smart_money_component = min(15, max(0, round((smart_money + 1) / 2 * 15)))
    bandar = min(20, max(0, round((smart_money_component + broker_component + foreign_component) / 30 * 20)))
    if bandarmology.get("verdict") == "akumulasi":
        bandar = min(20, bandar + 2)
    if bandarmology.get("verdict") == "distribusi":
        bandar = max(0, bandar - 4)
    macro = 10 if relative_strength >= 0 else 4
    sentiment = 3
    astro = 3
    breakdown = {
        "trend_score": int(trend_score),
        "momentum_score": int(momentum_score),
        "volume_liquidity_score": int(volume_score),
        "bandarmology_score": int(bandar),
        "smart_money_score": int(smart_money_component),
        "broker_accumulation": int(broker_component),
        "foreign_flow": int(foreign_component),
        "relative_strength": int(rs_score),
        "macro_risk_score": int(macro),
        "sentiment_score": int(sentiment),
        "astro_cycle_score": int(astro),
    }
    context = {
        "ma20": ma20,
        "ma50": ma50,
        "ma200": ma200,
        "volume_ratio_5d": volume_ratio,
        "relative_strength": relative_strength,
        "bandarmology": bandarmology.get("verdict", "netral"),
        "technical_indicators": technical_context,
        "breakdown": breakdown,
    }
    final_score = trend_score + momentum_score + volume_score + bandar + rs_score + macro + sentiment + astro
    return int(min(100, final_score)), breakdown, context


def entry_allowed(rule: str, score: int, context: dict[str, Any], latest: pd.Series) -> bool:
    normalized = rule.strip().lower()
    close = _safe_float(latest.close)
    if normalized in {"score_gt_80", "score>80"}:
        return score > 80
    if normalized in {"ma20_gt_ma50", "trend"}:
        return context.get("ma20", 0) > context.get("ma50", 0)
    if normalized in {"breakout", "near_breakout"}:
        return close >= _safe_float(context.get("resistance"), close) * 0.96
    if normalized in {"always", "all"}:
        return True
    return score > 70


def simulate_trade(df: pd.DataFrame, entry_index: int, horizon_days: int, stop_loss: float, target_profit: float, score: int) -> dict[str, Any] | None:
    if entry_index + 1 >= len(df):
        return None
    entry_row = df.iloc[entry_index]
    entry_price = _safe_float(entry_row.close)
    if entry_price <= 0:
        return None
    stop_price = entry_price * (1 - stop_loss)
    target_price = entry_price * (1 + target_profit)
    max_exit_index = min(entry_index + horizon_days, len(df) - 1)
    exit_index = max_exit_index
    exit_reason = "horizon"
    exit_price = _safe_float(df.iloc[exit_index].close)

    for index in range(entry_index + 1, max_exit_index + 1):
        row = df.iloc[index]
        if _safe_float(row.low) <= stop_price:
            exit_index = index
            exit_reason = "stop_loss"
            exit_price = stop_price
            break
        if _safe_float(row.high) >= target_price:
            exit_index = index
            exit_reason = "target_profit"
            exit_price = target_price
            break

    return {
        "entry_date": str(entry_row.date),
        "exit_date": str(df.iloc[exit_index].date),
        "entry_price": round(entry_price, 4),
        "exit_price": round(exit_price, 4),
        "return_pct": round(exit_price / entry_price - 1, 5),
        "score": int(score),
        "exit_reason": exit_reason,
    }


def summarize_trades(trades: list[dict[str, Any]]) -> dict[str, Any]:
    returns = [trade["return_pct"] for trade in trades]
    if not returns:
        return {
            "total_trade": 0,
            "win_rate": None,
            "average_return": None,
            "max_drawdown": None,
            "expectancy": None,
            "profit_factor": None,
            "best_trade": None,
            "worst_trade": None,
        }
    wins = [value for value in returns if value > 0]
    losses = [value for value in returns if value <= 0]
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    equity = pd.Series([1.0])
    for value in returns:
        equity.loc[len(equity)] = float(equity.iloc[-1]) * (1 + value)
    best = max(trades, key=lambda item: item["return_pct"])
    worst = min(trades, key=lambda item: item["return_pct"])
    avg_win = sum(wins) / len(wins) if wins else 0.0
    avg_loss = abs(sum(losses) / len(losses)) if losses else 0.0
    win_rate = len(wins) / len(returns)
    expectancy = win_rate * avg_win - (1 - win_rate) * avg_loss
    return {
        "total_trade": len(trades),
        "win_rate": round(win_rate, 4),
        "average_return": round(sum(returns) / len(returns), 5),
        "max_drawdown": round(_max_drawdown(equity), 5),
        "expectancy": round(expectancy, 5),
        "profit_factor": round(gross_profit / gross_loss, 4) if gross_loss > 0 else None,
        "best_trade": best,
        "worst_trade": worst,
    }


def screener_backtest_verdict(report: dict[str, Any]) -> dict[str, Any]:
    win_rate = report.get("win_rate")
    profit_factor = report.get("profit_factor")
    total_trade = int(report.get("total_trade") or 0)
    if total_trade < 8:
        verdict = "Backtest belum cukup."
    elif (win_rate or 0) >= 0.58 and (profit_factor or 0) >= 1.2:
        verdict = "Backtest mendukung."
    elif (win_rate or 0) >= 0.5:
        verdict = "Backtest netral."
    else:
        verdict = "Backtest lemah."
    return {"verdict": verdict, "win_rate": win_rate, "profit_factor": profit_factor}


def threshold_check(scored_rows: list[dict[str, Any]], threshold: int, random_average: float) -> dict[str, Any]:
    selected = [row["forward_return"] for row in scored_rows if row["score"] > threshold]
    if not selected:
        return {
            "threshold": threshold,
            "trade_count": 0,
            "win_rate": None,
            "average_forward_return": None,
            "random_average_return": round(random_average, 5),
            "better_than_random": None,
        }
    average = sum(selected) / len(selected)
    return {
        "threshold": threshold,
        "trade_count": len(selected),
        "win_rate": round(sum(1 for value in selected if value > 0) / len(selected), 4),
        "average_forward_return": round(average, 5),
        "random_average_return": round(random_average, 5),
        "better_than_random": average > random_average,
    }


async def run_idx_backtest(session: AsyncSession, request) -> dict[str, Any]:
    symbol = normalize_backend_ticker(request.ticker, "id")
    horizon_days = horizon_to_days(request.horizon)
    stop_loss = normalize_pct(float(request.stop_loss))
    target_profit = normalize_pct(float(request.target_profit))
    lookback_start = request.start_date - timedelta(days=260)
    df = await load_price_frame(session, symbol, max((request.end_date - lookback_start).days + 30, 320))
    df = df[(pd.to_datetime(df["date"]).dt.date >= lookback_start) & (pd.to_datetime(df["date"]).dt.date <= request.end_date)]
    df = df.sort_values("date").reset_index(drop=True)
    if len(df) < 80:
        raise ValueError("Data tidak cukup untuk backtest. Minimal sekitar 80 candle diperlukan.")

    benchmark_df = None
    try:
        benchmark_df = await load_price_frame(session, "^JKSE", max((request.end_date - lookback_start).days + 30, 320))
        benchmark_df = benchmark_df.sort_values("date").reset_index(drop=True)
    except Exception:
        benchmark_df = None

    trades: list[dict[str, Any]] = []
    scored_rows: list[dict[str, Any]] = []
    all_forward_returns: list[float] = []

    for index in range(60, len(df) - horizon_days):
        row_date = pd.to_datetime(df.iloc[index].date).date()
        if row_date < request.start_date or row_date > request.end_date:
            continue
        window = df.iloc[: index + 1].copy()
        benchmark_window = None
        if benchmark_df is not None:
            benchmark_window = benchmark_df[pd.to_datetime(benchmark_df["date"]).dt.date <= row_date].tail(len(window))
        score, _, context = compute_historical_score(window, benchmark_window)
        future_price = _safe_float(df.iloc[index + horizon_days].close)
        entry_price = _safe_float(df.iloc[index].close)
        forward_return = future_price / entry_price - 1 if entry_price > 0 else 0.0
        all_forward_returns.append(forward_return)
        scored_rows.append({"date": str(row_date), "score": score, "forward_return": forward_return})
        if entry_allowed(request.rule_entry, score, context, df.iloc[index]):
            trade = simulate_trade(df, index, horizon_days, stop_loss, target_profit, score)
            if trade:
                trades.append(trade)

    summary = summarize_trades(trades)
    random_average = sum(all_forward_returns) / len(all_forward_returns) if all_forward_returns else 0.0
    benchmark_return = None
    if benchmark_df is not None:
        bench_range = benchmark_df[
            (pd.to_datetime(benchmark_df["date"]).dt.date >= request.start_date)
            & (pd.to_datetime(benchmark_df["date"]).dt.date <= request.end_date)
        ]
        if len(bench_range) >= 2:
            benchmark_return = _safe_float(bench_range.iloc[-1].close) / _safe_float(bench_range.iloc[0].close, 1) - 1
    strategy_return = 1.0
    for trade in trades:
        strategy_return *= 1 + trade["return_pct"]
    strategy_total_return = strategy_return - 1

    return {
        "ticker": symbol,
        "start_date": request.start_date.isoformat(),
        "end_date": request.end_date.isoformat(),
        "horizon": request.horizon,
        "rule_entry": request.rule_entry,
        "rule_exit": request.rule_exit,
        **summary,
        "threshold_checks": [
            threshold_check(scored_rows, 70, random_average),
            threshold_check(scored_rows, 80, random_average),
        ],
        "benchmark": {
            "symbol": "^JKSE",
            "strategy_total_return": round(strategy_total_return, 5),
            "benchmark_return": round(benchmark_return, 5) if benchmark_return is not None else None,
            "beats_benchmark": strategy_total_return > benchmark_return if benchmark_return is not None else None,
        },
        "trades": trades[-100:],
    }


async def run_setup_backtest(session: AsyncSession, request) -> dict[str, Any]:
    """
    Backtest yang dipecah per setup type: breakout, pullback, continuation, reversal.

    Memberikan validasi statistik per jenis setup sehingga trader dapat mengetahui
    setup mana yang paling reliable untuk saham/pasar tertentu.

    Parameters
    ----------
    request : object dengan atribut:
        - ticker: str
        - start_date: date
        - end_date: date
        - horizon: str (e.g., "5d", "20d")
        - stop_loss: float (e.g., 0.03 = 3%)
        - target_profit: float (e.g., 0.06 = 6%)
    """
    SETUP_TYPES = ["breakout_candidate", "fresh_breakout", "pullback_to_support",
                   "trend_continuation", "reversal", "other"]

    symbol = normalize_backend_ticker(request.ticker, "id")
    horizon_days = horizon_to_days(request.horizon)
    stop_loss = normalize_pct(float(request.stop_loss))
    target_profit = normalize_pct(float(request.target_profit))
    lookback_start = request.start_date - timedelta(days=260)

    df = await load_price_frame(session, symbol, max((request.end_date - lookback_start).days + 30, 320))
    df = df[
        (pd.to_datetime(df["date"]).dt.date >= lookback_start)
        & (pd.to_datetime(df["date"]).dt.date <= request.end_date)
    ]
    df = df.sort_values("date").reset_index(drop=True)
    if len(df) < 80:
        raise ValueError("Data tidak cukup untuk setup backtest. Minimal 80 candle.")

    benchmark_df = None
    try:
        benchmark_df = await load_price_frame(session, "^JKSE", max((request.end_date - lookback_start).days + 30, 320))
        benchmark_df = benchmark_df.sort_values("date").reset_index(drop=True)
    except Exception:
        benchmark_df = None

    # Kelompokkan trade per setup type
    setup_trades: dict[str, list[dict[str, Any]]] = {st: [] for st in SETUP_TYPES}
    setup_scores: dict[str, list[int]] = {st: [] for st in SETUP_TYPES}

    for index in range(60, len(df) - horizon_days):
        row_date = pd.to_datetime(df.iloc[index].date).date()
        if row_date < request.start_date or row_date > request.end_date:
            continue

        window = df.iloc[: index + 1].copy()
        benchmark_window = None
        if benchmark_df is not None:
            benchmark_window = benchmark_df[pd.to_datetime(benchmark_df["date"]).dt.date <= row_date].tail(len(window))

        score, breakdown, context = compute_historical_score(window, benchmark_window)

        # Deteksi setup type dari context
        tech = context.get("technical_indicators", {})
        setup_type_raw = tech.get("setup_type", "other") or "other"

        # Normalisasi nama setup ke kategori standar
        if "breakout" in setup_type_raw and "fresh" not in setup_type_raw:
            setup_key = "breakout_candidate"
        elif "fresh" in setup_type_raw:
            setup_key = "fresh_breakout"
        elif "pullback" in setup_type_raw:
            setup_key = "pullback_to_support"
        elif "continuation" in setup_type_raw:
            setup_key = "trend_continuation"
        elif "reversal" in setup_type_raw:
            setup_key = "reversal"
        else:
            setup_key = "other"

        if score >= 55:  # Hanya backtest entry yang layak
            trade = simulate_trade(df, index, horizon_days, stop_loss, target_profit, score)
            if trade:
                trade["setup_type"] = setup_key
                setup_trades[setup_key].append(trade)
                setup_scores[setup_key].append(score)

    # Summarize per setup
    setup_performance: dict[str, Any] = {}
    for setup_type, trades in setup_trades.items():
        if not trades:
            setup_performance[setup_type] = {
                "setup_type": setup_type,
                "total_trades": 0,
                "win_rate": None,
                "average_return": None,
                "max_drawdown": None,
                "profit_factor": None,
                "expectancy": None,
                "avg_score": None,
                "verdict": "Tidak ada trade yang memenuhi kriteria.",
            }
            continue

        summary_data = summarize_trades(trades)
        avg_score = round(sum(setup_scores[setup_type]) / len(setup_scores[setup_type])) if setup_scores[setup_type] else 0

        # Verdict per setup
        wr = summary_data.get("win_rate") or 0
        pf = summary_data.get("profit_factor") or 0
        tt = summary_data.get("total_trade") or 0
        if tt < 5:
            verdict = "Sampel belum cukup."
        elif wr >= 0.60 and pf >= 1.5:
            verdict = "⭐ Setup unggulan — Win rate dan profit factor sangat baik."
        elif wr >= 0.55 and pf >= 1.2:
            verdict = "✅ Setup reliabel — Performa positif dan konsisten."
        elif wr >= 0.50:
            verdict = "⚠️ Setup cukup — Performa marginal, gunakan dengan selektif."
        else:
            verdict = "❌ Setup lemah — Win rate di bawah 50%, hindari setup ini."

        setup_performance[setup_type] = {
            "setup_type": setup_type,
            "total_trades": tt,
            "win_rate": summary_data.get("win_rate"),
            "average_return": summary_data.get("average_return"),
            "max_drawdown": summary_data.get("max_drawdown"),
            "profit_factor": summary_data.get("profit_factor"),
            "expectancy": summary_data.get("expectancy"),
            "best_trade": summary_data.get("best_trade"),
            "worst_trade": summary_data.get("worst_trade"),
            "avg_score": avg_score,
            "verdict": verdict,
        }

    # Ranking setup berdasarkan win_rate * profit_factor
    ranked_setups = sorted(
        [v for v in setup_performance.values() if v.get("win_rate") is not None],
        key=lambda x: (x.get("win_rate") or 0) * (x.get("profit_factor") or 0),
        reverse=True,
    )

    best_setup = ranked_setups[0]["setup_type"] if ranked_setups else None

    return {
        "ticker": symbol,
        "start_date": request.start_date.isoformat(),
        "end_date": request.end_date.isoformat(),
        "horizon": request.horizon,
        "stop_loss": stop_loss,
        "target_profit": target_profit,
        "setup_performance": setup_performance,
        "ranked_setups": [s["setup_type"] for s in ranked_setups],
        "best_setup": best_setup,
        "best_setup_note": (
            f"Setup '{best_setup}' menunjukkan performa terbaik berdasarkan "
            f"kombinasi win rate dan profit factor untuk {symbol}."
            if best_setup else "Belum ada data setup yang cukup."
        ),
    }




async def run_idx_screener(session: AsyncSession, request) -> dict[str, Any]:
    raw_universe = request.tickers or IDX_UNIVERSE
    universe = [normalize_backend_ticker(ticker, "id") for ticker in raw_universe if ticker.strip()]
    buckets = {"daily": [], "weekly": [], "monthly": []}
    avoid: list[dict[str, Any]] = []
    gorengan_watchlist: list[dict[str, Any]] = []  # Saham gorengan dengan WARNING

    for symbol in universe:
        try:
            df = await load_price_frame(session, symbol, 320)
            if len(df) < 80:
                continue
            enriched = enrich_ohlcv(df).reset_index(drop=True)

            avg_volume_20 = _safe_float(enriched["volume"].astype(float).tail(20).mean())
            avg_value_20 = avg_volume_20 * _safe_float(enriched["close"].astype(float).tail(20).mean())

            # ── Liquidity Analysis (WARNING, bukan hard-skip) ─────────
            liq = analyze_liquidity(enriched, symbol=symbol)

            reports = {
                label: await build_idx_recommendation(session, symbol, horizon=label, market="id")
                for label in ("daily", "weekly", "monthly")
            }
            bandarmology = build_bandarmology(enriched, symbol)
            for label, report in reports.items():
                price_context = report["price_context"]
                pass_filters = (
                    price_context["volume_ratio_5d"] >= 1.0
                    and (
                        report["last_price"] >= _safe_float(price_context.get("ma20"), report["last_price"])
                        or report["last_price"] >= _safe_float(price_context.get("resistance"), report["last_price"]) * 0.96
                    )
                    and _safe_float(price_context.get("ma20")) >= _safe_float(price_context.get("ma50"))
                    and price_context["relative_strength"] > 0
                    and report["risk_reward"] >= 1.5
                )
                if bandarmology.get("verdict") == "akumulasi":
                    pass_filters = pass_filters and True

                # ── Build item dengan Liquidity WARNING fields ────────
                item = {
                    "symbol": symbol,
                    "final_score": report["final_score"],
                    "signal": report["signal"],
                    "calibrated_probability": report.get("calibrated_probability"),
                    "horizon": label,
                    "last_price": report["last_price"],
                    "entry_zone": report["entry_zone"],
                    "target_1": report["target_1"],
                    "target_2": report["target_2"],
                    "target_3": report.get("target_3"),
                    "stop_loss": report["stop_loss"],
                    "risk_reward": report["risk_reward"],
                    "avg_volume_20d": round(avg_volume_20, 2),
                    "avg_value_20d": round(avg_value_20, 2),
                    "volume_ratio_5d": price_context["volume_ratio_5d"],
                    "relative_strength": price_context["relative_strength"],
                    "bandarmology": bandarmology.get("verdict", "netral"),
                    "setup_type": report.get("technical_indicators", {}).get("setup_type"),
                    "market_structure": report.get("technical_indicators", {}).get("market_structure"),
                    "trend_state": report.get("technical_indicators", {}).get("trend_state"),
                    "backtest_confidence": None,
                    "backtest_win_rate": None,
                    "backtest_profit_factor": None,
                    "reasons": report["main_reasons"],
                    "risks": report["main_risks"],
                    # ── Liquidity & Gorengan WARNING ─────────────────
                    "liquidity_grade": liq.liquidity_grade,
                    "is_gorengan": liq.is_gorengan,
                    "gorengan_risk_level": liq.gorengan_risk_level,
                    "liquidity_summary": liq.summary,
                    "liquidity_recommendation": liq.recommendation,
                    "liquidity_warnings": [
                        {"code": w.code, "severity": w.severity, "message": w.message}
                        for w in liq.warnings
                    ],
                }
                if label == horizon_label(request.horizon):
                    try:
                        backtest_report = await run_idx_backtest(
                            session,
                            type(
                                "ScreenerBacktestRequest",
                                (),
                                {
                                    "ticker": symbol,
                                    "start_date": date.today() - timedelta(days=540),
                                    "end_date": date.today(),
                                    "horizon": f"{horizon_to_days(label)}d",
                                    "rule_entry": "score_gt_70",
                                    "rule_exit": "target_stop_or_horizon",
                                    "stop_loss": 0.03,
                                    "target_profit": 0.06,
                                },
                            )(),
                        )
                        confidence = screener_backtest_verdict(backtest_report)
                        item["backtest_confidence"] = confidence["verdict"]
                        item["backtest_win_rate"] = confidence["win_rate"]
                        item["backtest_profit_factor"] = confidence["profit_factor"]
                    except Exception:
                        item["backtest_confidence"] = "Backtest belum tersedia."

                # ── Routing: Normal, Gorengan Watchlist, atau Avoid ──
                if liq.is_gorengan and liq.gorengan_risk_level in ("high", "extreme"):
                    # Saham gorengan risiko tinggi: tampilkan di gorengan_watchlist
                    if label == horizon_label(request.horizon):
                        gorengan_watchlist.append(item)
                elif pass_filters and report["final_score"] >= 58:
                    buckets[label].append(item)
                elif label == horizon_label(request.horizon) and (report["final_score"] < 45 or bandarmology.get("verdict") == "distribusi"):
                    avoid.append(item)
        except Exception:
            continue

    # ── Sort awal berdasarkan skor teknikal ─────────────────────────────────
    for label in buckets:
        buckets[label].sort(
            key=lambda item: (item["final_score"], item["risk_reward"], item["relative_strength"]),
            reverse=True,
        )
    avoid.sort(key=lambda item: (item["final_score"], item["risk_reward"]))
    gorengan_watchlist.sort(key=lambda item: item["final_score"], reverse=True)

    # ── Lapis 5: News Sentiment Weighting ────────────────────────────────────
    # Kumpulkan semua ticker yang lolos untuk di-fetch beritanya sekaligus
    all_passed_tickers = list({
        item["symbol"]
        for label_items in buckets.values()
        for item in label_items
    })
    news_data_available = False
    try:
        sentiment_map = await fetch_news_sentiment(all_passed_tickers)
        news_data_available = any(
            s.headline_count > 0 for s in sentiment_map.values()
        )
        # Terapkan pembobotan sentimen dan sort ulang
        for label in buckets:
            buckets[label] = apply_news_sentiment_weighting(
                buckets[label], sentiment_map
            )
        # Gorengan watchlist juga di-weight (tanpa mengubah posisi avoid)
        gorengan_watchlist = apply_news_sentiment_weighting(
            gorengan_watchlist, sentiment_map
        )
    except Exception:
        # Jika fetch berita gagal, tetap tampilkan hasil tanpa sentimen
        for label in buckets:
            for item in buckets[label]:
                item["news_sentiment_score"] = 0.5
                item["news_sentiment_label"] = "neutral"
                item["news_headlines"] = []
                item["final_weighted_score"] = item["final_score"]

    # ── top_n: 0 atau None = tampilkan semua yang lolos ──────────────────────
    top_n = getattr(request, "top_n", 0) or 0
    def _limit(lst: list) -> list:
        return lst if top_n <= 0 else lst[:top_n]

    total_daily   = len(buckets["daily"])
    total_weekly  = len(buckets["weekly"])
    total_monthly = len(buckets["monthly"])

    return {
        "horizon": request.horizon,
        "universe_size": len(universe),
        "scanned_size": total_daily + total_weekly + total_monthly,
        # Jumlah saham yang lolos per timeframe (tanpa batas)
        "total_daily": total_daily,
        "total_weekly": total_weekly,
        "total_monthly": total_monthly,
        "top_daily": _limit(buckets["daily"]),
        "top_weekly": _limit(buckets["weekly"]),
        "top_monthly": _limit(buckets["monthly"]),
        "avoid_high_risk": _limit(avoid),
        "gorengan_watchlist": _limit(gorengan_watchlist),
        "gorengan_watchlist_note": (
            "\u26a0\ufe0f PERINGATAN: Saham-saham berikut memiliki indikasi sebagai saham gorengan/manipulasi. "
            "Ditampilkan untuk transparansi. Trader bertanggung jawab penuh atas keputusan transaksi."
        ),
        # ── Lapis 5: Metadata sentimen berita ───────────────────────────────
        "news_data_available": news_data_available,
        "news_weighting_note": (
            "Ranking final = 75% Skor Teknikal + 25% Sentimen Berita. "
            "Sentimen dihitung dari RSS Yahoo Finance dan IDX secara real-time."
            if news_data_available
            else "Data berita belum tersedia. Ranking berdasarkan skor teknikal saja."
        ),
    }
