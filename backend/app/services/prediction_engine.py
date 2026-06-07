from dataclasses import dataclass
from datetime import date, timedelta
import math

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import MarketPrice, ModelWeightProfile, PredictionSnapshot
from backend.app.services.composite_engine import CycleCombination, calculate_composite_cycle
from backend.app.services.context_engine import build_macro_context, build_sentiment_context
from backend.app.services.market import fetch_market_data


DEFAULT_COMBINATIONS = [
    CycleCombination("Venus", "Jupiter", 1.0),
    CycleCombination("Moon", "Saturn", 1.0),
    CycleCombination("Mercury", "Mars", 0.8),
]

DEFAULT_WEIGHTS = {
    "momentum_20": 0.26,
    "trend_50": 0.24,
    "astro_cycle": 0.22,
    "volume_pressure": 0.12,
    "volatility": 0.16,
}


@dataclass
class Factor:
    key: str
    name: str
    value: float
    weight: float
    description: str

    @property
    def contribution(self) -> float:
        return self.value * self.weight


def clamp(value: float, lower: float = -1.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def normalize_backend_ticker(value: str, market: str = "us") -> str:
    symbol = value.strip().upper()
    if not symbol:
        return ""
    if market == "id" and "." not in symbol:
        return f"{symbol}.JK"
    return symbol


def sigmoid(value: float) -> float:
    return 1 / (1 + math.exp(-value))


def detect_regime(df: pd.DataFrame) -> dict[str, float | str]:
    close = df["close"].astype(float)
    returns = close.pct_change().fillna(0)
    latest_close = float(close.iloc[-1])
    sma_50 = float(close.rolling(50, min_periods=10).mean().iloc[-1])
    sma_200 = float(close.rolling(200, min_periods=30).mean().iloc[-1])
    return_20 = latest_close / float(close.iloc[-21]) - 1 if len(close) > 21 else 0.0
    return_60 = latest_close / float(close.iloc[-61]) - 1 if len(close) > 61 else return_20
    realized_volatility = float(returns.rolling(20, min_periods=10).std().iloc[-1] or 0) * math.sqrt(252)

    trend_score = clamp(((latest_close / sma_50 - 1) * 6 if sma_50 else 0) + ((latest_close / sma_200 - 1) * 4 if sma_200 else 0))
    momentum_score = clamp((return_20 * 5) + (return_60 * 2.5))
    volatility_score = clamp(realized_volatility / 0.45, 0, 1)

    if volatility_score >= 0.78 and momentum_score < -0.15:
        label = "risk-off"
        risk_multiplier = 0.55
        description = "Volatilitas tinggi dan momentum melemah. Prioritaskan proteksi risiko."
    elif trend_score > 0.22 and momentum_score > 0.12 and volatility_score < 0.65:
        label = "bullish"
        risk_multiplier = 1.05
        description = "Trend dan momentum mendukung skenario konstruktif."
    elif trend_score < -0.22 and momentum_score < -0.12:
        label = "bearish"
        risk_multiplier = 0.65
        description = "Trend dan momentum masih menekan harga."
    elif volatility_score >= 0.72:
        label = "high-volatility"
        risk_multiplier = 0.70
        description = "Volatilitas tinggi. Ukuran posisi sebaiknya lebih konservatif."
    else:
        label = "sideways"
        risk_multiplier = 0.85
        description = "Pasar relatif campuran. Tunggu konfirmasi breakout atau breakdown."

    return {
        "label": label,
        "trend_score": trend_score,
        "volatility_score": volatility_score,
        "momentum_score": momentum_score,
        "risk_multiplier": risk_multiplier,
        "description": description,
    }


async def load_price_frame(session: AsyncSession, ticker: str, lookback_days: int = 420) -> pd.DataFrame:
    symbol = ticker.upper()
    query = (
        select(MarketPrice)
        .where(MarketPrice.symbol == symbol)
        .order_by(MarketPrice.date)
    )
    result = await session.execute(query)
    rows = result.scalars().all()

    if not rows:
        end = date.today() + timedelta(days=1)
        start = end - timedelta(days=lookback_days)
        fetched = fetch_market_data(symbol, start, end)
        fetched["date"] = pd.to_datetime(fetched["date"]).dt.date
        rows_to_insert = [
            MarketPrice(
                symbol=symbol,
                date=row.date,
                open=float(row.open),
                high=float(row.high),
                low=float(row.low),
                close=float(row.close),
                volume=float(row.volume),
            )
            for row in fetched.itertuples(index=False)
        ]
        session.add_all(rows_to_insert)
        await session.commit()
        rows = rows_to_insert

    data = [
        {
            "date": row.date,
            "open": row.open,
            "high": row.high,
            "low": row.low,
            "close": row.close,
            "volume": row.volume or 0,
        }
        for row in rows
    ]
    df = pd.DataFrame(data).sort_values("date")
    return df.tail(lookback_days).reset_index(drop=True)


async def latest_composite_value(session: AsyncSession, as_of_date: date) -> float:
    start_date = as_of_date - timedelta(days=60)
    composite = await calculate_composite_cycle(session, DEFAULT_COMBINATIONS, start_date, as_of_date)
    if not composite:
        return 0.0
    return float(composite[-1]["value"])


def normalize_weights(raw_weights: dict[str, float]) -> dict[str, float]:
    cleaned = {key: max(0.0, float(raw_weights.get(key, 0))) for key in DEFAULT_WEIGHTS}
    total = sum(cleaned.values())
    if total <= 0:
        return DEFAULT_WEIGHTS.copy()
    return {key: value / total for key, value in cleaned.items()}


def extract_factor_values(df: pd.DataFrame, composite_value: float) -> dict[str, float]:
    close = df["close"].astype(float)
    volume = df["volume"].astype(float)
    returns = close.pct_change().fillna(0)

    latest_close = float(close.iloc[-1])
    momentum_20 = (latest_close / float(close.iloc[-21]) - 1) if len(close) > 21 else 0
    sma_50 = float(close.rolling(50, min_periods=5).mean().iloc[-1])
    trend_50 = latest_close / sma_50 - 1 if sma_50 else 0
    volatility_20 = float(returns.rolling(20, min_periods=5).std().iloc[-1] or 0)
    volume_ratio = (
        float(volume.iloc[-5:].mean()) / float(volume.rolling(30, min_periods=5).mean().iloc[-1]) - 1
        if float(volume.rolling(30, min_periods=5).mean().iloc[-1] or 0) > 0
        else 0
    )

    return {
        "momentum_20": clamp(momentum_20 * 8),
        "trend_50": clamp(trend_50 * 10),
        "astro_cycle": clamp(composite_value),
        "volume_pressure": clamp(volume_ratio),
        "volatility": clamp(-volatility_20 * 12),
    }


def score_from_frame(
    df: pd.DataFrame,
    composite_value: float,
    weights: dict[str, float] | None = None,
) -> tuple[list[Factor], float, float, str, str, str]:
    close = df["close"].astype(float)
    returns = close.pct_change().fillna(0)
    volatility_20 = float(returns.rolling(20, min_periods=5).std().iloc[-1] or 0)
    selected_weights = normalize_weights(weights or DEFAULT_WEIGHTS)
    values = extract_factor_values(df, composite_value)

    factors = [
        Factor("momentum_20", "Momentum 20 Hari", values["momentum_20"], selected_weights["momentum_20"], "Perubahan harga 20 hari terakhir."),
        Factor("trend_50", "Trend 50 Hari", values["trend_50"], selected_weights["trend_50"], "Posisi harga terhadap rata-rata 50 hari."),
        Factor("astro_cycle", "Siklus Astro", values["astro_cycle"], selected_weights["astro_cycle"], "Nilai siklus komposit planet terbaru."),
        Factor("volume_pressure", "Volume Pressure", values["volume_pressure"], selected_weights["volume_pressure"], "Volume terbaru dibanding rata-rata 30 hari."),
        Factor("volatility", "Volatilitas", values["volatility"], selected_weights["volatility"], "Volatilitas tinggi menurunkan confidence."),
    ]

    regime = detect_regime(df)
    score = sum(factor.contribution for factor in factors)
    if regime["label"] == "bullish":
        score += 0.08
    elif regime["label"] in {"bearish", "risk-off"}:
        score -= 0.08
    elif regime["label"] == "high-volatility":
        score *= 0.86

    probability_up = sigmoid(score * 2.2)
    expected_return = (probability_up - 0.5) * 0.16 * float(regime["risk_multiplier"])

    if probability_up >= 0.62:
        signal = "bullish"
    elif probability_up <= 0.38:
        signal = "bearish"
    else:
        signal = "netral"

    confidence_gap = abs(probability_up - 0.5)
    if confidence_gap >= 0.22 and volatility_20 < 0.035:
        confidence = "tinggi"
    elif confidence_gap >= 0.12:
        confidence = "sedang"
    else:
        confidence = "rendah"

    if regime["label"] in {"risk-off", "high-volatility"}:
        confidence = "rendah" if confidence != "tinggi" else "sedang"

    risk_label = "tinggi" if regime["label"] in {"risk-off", "high-volatility"} or volatility_20 >= 0.035 else "sedang" if volatility_20 >= 0.02 else "rendah"
    return factors, probability_up, expected_return, signal, confidence, risk_label


def build_scenario_plan(
    df: pd.DataFrame,
    signal: str,
    expected_return: float,
    risk_label: str,
    risk_budget: str,
    account_equity: float = 10000,
    risk_pct: float = 1.0,
) -> dict:
    close = df["close"].astype(float)
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    latest_close = float(close.iloc[-1])
    true_range = pd.concat(
        [
            high - low,
            (high - close.shift(1)).abs(),
            (low - close.shift(1)).abs(),
        ],
        axis=1,
    ).max(axis=1)
    atr_14 = float(true_range.rolling(14, min_periods=5).mean().iloc[-1] or latest_close * 0.03)
    budget_multiplier = 0.6 if risk_budget == "defensif" else 1.1 if risk_budget == "agresif-terukur" else 0.85
    risk_amount = account_equity * (risk_pct / 100) * budget_multiplier
    stop_distance = max(atr_14 * (1.2 if risk_label == "tinggi" else 1.0), latest_close * 0.015)

    if signal == "bearish":
        entry_low = latest_close - atr_14 * 0.15
        entry_high = latest_close + atr_14 * 0.25
        invalidation = latest_close + stop_distance
        bullish_target = latest_close + abs(expected_return) * latest_close
        bearish_target = latest_close - max(abs(expected_return) * latest_close, atr_14 * 1.8)
        playbook = "Bias bearish. Prioritaskan sell rally atau hindari entry long sampai harga kembali melewati invalidation."
    else:
        entry_low = latest_close - atr_14 * 0.35
        entry_high = latest_close + atr_14 * 0.15
        invalidation = latest_close - stop_distance
        bullish_target = latest_close + max(abs(expected_return) * latest_close, atr_14 * 1.8)
        bearish_target = latest_close - abs(expected_return) * latest_close
        playbook = "Bias konstruktif. Entry terbaik berada dekat entry zone dengan stop disiplin di invalidation."

    risk_per_share = abs(latest_close - invalidation)
    position_size = int(risk_amount / risk_per_share) if risk_per_share > 0 else 0
    return {
        "entry_zone_low": round(entry_low, 2),
        "entry_zone_high": round(entry_high, 2),
        "invalidation_level": round(invalidation, 2),
        "bullish_target": round(bullish_target, 2),
        "bearish_target": round(bearish_target, 2),
        "position_size_shares": max(position_size, 0),
        "risk_amount": round(risk_amount, 2),
        "risk_per_share": round(risk_per_share, 2),
        "playbook": playbook,
    }


def backtest_frame(df: pd.DataFrame, horizon_days: int, weights: dict[str, float] | None = None) -> dict[str, float | int]:
    if len(df) < 90 + horizon_days:
        return {
            "sample_count": 0,
            "hit_rate": 0.0,
            "average_forward_return": 0.0,
            "average_signal_return": 0.0,
            "max_drawdown": 0.0,
        }

    closes = df["close"].astype(float).reset_index(drop=True)
    returns = closes.pct_change().fillna(0)
    signal_returns = []
    hits = 0

    for idx in range(60, len(df) - horizon_days):
        window = pd.DataFrame({
            "close": closes.iloc[: idx + 1],
            "volume": df["volume"].astype(float).iloc[: idx + 1],
        })
        factors, probability_up, _, signal, _, _ = score_from_frame(window, 0.0, weights)
        forward_return = float(closes.iloc[idx + horizon_days] / closes.iloc[idx] - 1)
        direction = 1 if signal != "bearish" else -1
        signal_return = direction * forward_return
        signal_returns.append(signal_return)
        if signal_return > 0:
            hits += 1

    equity = pd.Series(signal_returns).fillna(0).add(1).cumprod()
    drawdown = equity / equity.cummax() - 1 if not equity.empty else pd.Series([0])
    sample_count = len(signal_returns)

    return {
        "sample_count": sample_count,
        "hit_rate": hits / sample_count if sample_count else 0.0,
        "average_forward_return": float(returns.tail(horizon_days).sum()),
        "average_signal_return": float(pd.Series(signal_returns).mean()) if sample_count else 0.0,
        "max_drawdown": float(drawdown.min()) if not drawdown.empty else 0.0,
    }


async def get_weight_profile(
    session: AsyncSession,
    symbol: str,
    horizon_days: int,
) -> ModelWeightProfile | None:
    result = await session.execute(
        select(ModelWeightProfile)
        .where(ModelWeightProfile.symbol == symbol.upper())
        .where(ModelWeightProfile.horizon_days == horizon_days)
    )
    return result.scalar_one_or_none()


def learn_weights_from_frame(df: pd.DataFrame, horizon_days: int) -> tuple[dict[str, float], dict[str, float | int]]:
    if len(df) < 120 + horizon_days:
        metrics = backtest_frame(df, horizon_days, DEFAULT_WEIGHTS)
        return DEFAULT_WEIGHTS.copy(), metrics

    rows = []
    closes = df["close"].astype(float).reset_index(drop=True)
    for idx in range(60, len(df) - horizon_days):
        window = df.iloc[: idx + 1].reset_index(drop=True)
        factor_values = extract_factor_values(window, 0.0)
        forward_return = float(closes.iloc[idx + horizon_days] / closes.iloc[idx] - 1)
        rows.append({**factor_values, "forward_return": forward_return})

    learn_df = pd.DataFrame(rows)
    raw_weights = {}
    for key in DEFAULT_WEIGHTS:
        correlation = learn_df[key].corr(learn_df["forward_return"])
        if pd.isna(correlation):
            correlation = 0.0
        raw_weights[key] = abs(float(correlation)) + 0.03

    learned_weights = normalize_weights(raw_weights)
    learned_metrics = backtest_frame(df, horizon_days, learned_weights)
    default_metrics = backtest_frame(df, horizon_days, DEFAULT_WEIGHTS)

    if float(default_metrics["average_signal_return"]) > float(learned_metrics["average_signal_return"]):
        return DEFAULT_WEIGHTS.copy(), default_metrics
    return learned_weights, learned_metrics


async def train_weight_profile(session: AsyncSession, ticker: str, horizon_days: int = 30) -> dict:
    symbol = ticker.upper()
    df = await load_price_frame(session, symbol, lookback_days=720)
    weights, metrics = learn_weights_from_frame(df, horizon_days)

    profile = await get_weight_profile(session, symbol, horizon_days)
    if profile:
        profile.weights = weights
        profile.sample_count = int(metrics["sample_count"])
        profile.hit_rate = float(metrics["hit_rate"])
        profile.average_signal_return = float(metrics["average_signal_return"])
        profile.method = "correlation_learning"
    else:
        profile = ModelWeightProfile(
            symbol=symbol,
            horizon_days=horizon_days,
            weights=weights,
            sample_count=int(metrics["sample_count"]),
            hit_rate=float(metrics["hit_rate"]),
            average_signal_return=float(metrics["average_signal_return"]),
            method="correlation_learning",
        )
        session.add(profile)

    await session.commit()
    await session.refresh(profile)
    return profile_to_dict(profile)


def profile_to_dict(profile: ModelWeightProfile | None, ticker: str | None = None, horizon_days: int = 30) -> dict:
    if profile is None:
        return {
            "ticker": (ticker or "").upper(),
            "horizon_days": horizon_days,
            "weights": DEFAULT_WEIGHTS.copy(),
            "sample_count": 0,
            "hit_rate": 0.0,
            "average_signal_return": 0.0,
            "method": "default",
            "trained_at": None,
        }
    return {
        "ticker": profile.symbol,
        "horizon_days": profile.horizon_days,
        "weights": profile.weights,
        "sample_count": profile.sample_count,
        "hit_rate": profile.hit_rate,
        "average_signal_return": profile.average_signal_return,
        "method": profile.method,
        "trained_at": profile.trained_at.isoformat() if profile.trained_at else None,
    }


async def build_prediction(
    session: AsyncSession,
    ticker: str,
    horizon_days: int = 30,
    account_equity: float = 10000,
    risk_pct: float = 1.0,
) -> dict:
    symbol = ticker.upper()
    df = await load_price_frame(session, ticker)
    if df.empty or len(df) < 30:
        raise ValueError("Data harga belum cukup untuk membuat prediksi.")

    as_of_date = df.iloc[-1]["date"]
    composite_value = await latest_composite_value(session, as_of_date)
    profile = await get_weight_profile(session, symbol, horizon_days)
    if profile is None:
        await train_weight_profile(session, symbol, horizon_days)
        profile = await get_weight_profile(session, symbol, horizon_days)
    active_weights = profile.weights if profile else DEFAULT_WEIGHTS
    factors, probability_up, expected_return, signal, confidence, risk_label = score_from_frame(df, composite_value, active_weights)
    backtest = backtest_frame(df, horizon_days, active_weights)
    regime = detect_regime(df)
    sentiment = await build_sentiment_context(symbol)
    macro = await build_macro_context(session, symbol)

    expected_return += float(sentiment["score"]) * 0.015
    if macro["risk_budget"] == "defensif":
        expected_return *= 0.75
        risk_label = "tinggi" if risk_label != "tinggi" else risk_label
    elif macro["risk_budget"] == "agresif-terukur":
        expected_return *= 1.08
    scenario = build_scenario_plan(df, signal, expected_return, risk_label, str(macro["risk_budget"]), account_equity, risk_pct)

    snapshot = PredictionSnapshot(
        symbol=symbol,
        as_of_date=as_of_date,
        horizon_days=horizon_days,
        score=sum(factor.contribution for factor in factors),
        probability_up=probability_up,
        confidence=confidence,
        signal=signal,
        expected_return=expected_return,
    )
    session.add(snapshot)
    try:
        await session.commit()
    except Exception:
        await session.rollback()

    return {
        "ticker": symbol,
        "as_of_date": as_of_date.isoformat(),
        "horizon_days": horizon_days,
        "signal": signal,
        "probability_up": probability_up,
        "confidence": confidence,
        "expected_return": expected_return,
        "risk_label": risk_label,
        "regime": regime,
        "sentiment": sentiment,
        "macro": macro,
        "scenario": scenario,
        "factors": [
            {
                "name": factor.name,
                "value": factor.value,
                "weight": factor.weight,
                "contribution": factor.contribution,
                "description": factor.description,
            }
            for factor in factors
        ],
        "backtest": backtest,
    }


async def build_performance_report(session: AsyncSession, ticker: str, horizon_days: int = 30) -> dict:
    symbol = ticker.upper()
    df = await load_price_frame(session, symbol, lookback_days=720)
    if df.empty or len(df) < 90:
        raise ValueError("Data harga belum cukup untuk performance report.")

    model_weights = await train_weight_profile(session, symbol, horizon_days)
    latest_prediction = await build_prediction(session, symbol, horizon_days)
    backtest = backtest_frame(df, horizon_days, model_weights["weights"])

    snapshot_result = await session.execute(
        select(PredictionSnapshot)
        .where(PredictionSnapshot.symbol == symbol)
        .where(PredictionSnapshot.horizon_days == horizon_days)
        .order_by(PredictionSnapshot.as_of_date.desc())
        .limit(20)
    )
    snapshots = snapshot_result.scalars().all()

    close_by_date = {row.date: float(row.close) for row in await get_market_rows(session, symbol)}
    snapshot_rows = []
    for snapshot in snapshots:
        realized_return = snapshot.realized_return
        target_date = snapshot.as_of_date + timedelta(days=horizon_days)
        if realized_return is None and snapshot.as_of_date in close_by_date:
            future_dates = [item_date for item_date in close_by_date if item_date >= target_date]
            if future_dates:
                future_date = min(future_dates)
                realized_return = close_by_date[future_date] / close_by_date[snapshot.as_of_date] - 1
                snapshot.realized_return = realized_return

        snapshot_rows.append(
            {
                "as_of_date": snapshot.as_of_date.isoformat(),
                "horizon_days": snapshot.horizon_days,
                "signal": snapshot.signal,
                "probability_up": snapshot.probability_up,
                "confidence": snapshot.confidence,
                "expected_return": snapshot.expected_return,
                "realized_return": realized_return,
            }
        )

    if snapshots:
        await session.commit()

    hit_rate = float(backtest["hit_rate"])
    sample_count = int(backtest["sample_count"])
    if sample_count < 30:
        verdict = "Data historis belum cukup untuk menilai kualitas model."
    elif hit_rate >= 0.58:
        verdict = "Model terlihat konstruktif pada backtest awal, tetapi tetap perlu validasi forward."
    elif hit_rate >= 0.50:
        verdict = "Model cukup netral; gunakan sebagai filter pendukung, bukan sinyal tunggal."
    else:
        verdict = "Model belum stabil untuk ticker ini; bobot faktor perlu dievaluasi ulang."

    return {
        "ticker": symbol,
        "horizon_days": horizon_days,
        "backtest": backtest,
        "latest_prediction": latest_prediction,
        "model_weights": model_weights,
        "snapshots": snapshot_rows,
        "verdict": verdict,
    }


async def build_watchlist(session: AsyncSession, tickers: list[str], horizon_days: int = 30) -> dict:
    items = []
    for ticker in tickers:
        symbol = ticker.strip().upper()
        if not symbol:
            continue
        try:
            prediction = await build_prediction(session, symbol, horizon_days)
            items.append(
                {
                    "ticker": symbol,
                    "signal": prediction["signal"],
                    "probability_up": prediction["probability_up"],
                    "confidence": prediction["confidence"],
                    "expected_return": prediction["expected_return"],
                    "risk_label": prediction["risk_label"],
                    "regime": prediction["regime"]["label"],
                    "sentiment": prediction["sentiment"]["label"] if prediction.get("sentiment") else "netral",
                    "risk_budget": prediction["macro"]["risk_budget"] if prediction.get("macro") else "normal",
                }
            )
        except Exception:
            continue

    items.sort(
        key=lambda item: (
            item["expected_return"],
            item["probability_up"],
            -1 if item["risk_label"] == "tinggi" else 0,
        ),
        reverse=True,
    )
    return {"horizon_days": horizon_days, "items": items}


async def build_idx_workflow(
    session: AsyncSession,
    tickers: list[str],
    market: str = "id",
    daily_horizon: int = 5,
    weekly_horizon: int = 20,
    monthly_horizon: int = 60,
) -> dict:
    universe = [normalize_backend_ticker(ticker, market) for ticker in tickers if ticker.strip()]
    items = []

    for symbol in universe:
        try:
            daily = await build_prediction(session, symbol, daily_horizon)
            weekly = await build_prediction(session, symbol, weekly_horizon)
            monthly = await build_prediction(session, symbol, monthly_horizon)
        except Exception:
            continue

        predictions = [daily, weekly, monthly]
        bullish_count = sum(1 for prediction in predictions if prediction["signal"] == "bullish")
        bearish_count = sum(1 for prediction in predictions if prediction["signal"] == "bearish")
        avg_probability = sum(float(prediction["probability_up"]) for prediction in predictions) / 3
        avg_expected_return = sum(float(prediction["expected_return"]) for prediction in predictions) / 3
        avg_confidence_bonus = {"tinggi": 0.08, "sedang": 0.04, "rendah": 0.0}
        confidence_score = sum(avg_confidence_bonus.get(prediction["confidence"], 0.0) for prediction in predictions) / 3

        latest = monthly
        latest_scenario = latest.get("scenario") or {}
        entry_low = min(
            float(daily["scenario"]["entry_zone_low"]),
            float(weekly["scenario"]["entry_zone_low"]),
            float(monthly["scenario"]["entry_zone_low"]),
        )
        entry_high = min(
            float(daily["scenario"]["entry_zone_high"]),
            float(weekly["scenario"]["entry_zone_high"]),
            float(monthly["scenario"]["entry_zone_high"]),
        )
        target_price = max(
            float(daily["scenario"]["bullish_target"]),
            float(weekly["scenario"]["bullish_target"]),
            float(monthly["scenario"]["bullish_target"]),
        )
        stop_loss = min(
            float(daily["scenario"]["invalidation_level"]),
            float(weekly["scenario"]["invalidation_level"]),
            float(monthly["scenario"]["invalidation_level"]),
        )

        if monthly["signal"] == "bearish" or weekly["signal"] == "bearish":
            recommended_action = "tunggu"
        elif monthly["signal"] == "bullish" and weekly["signal"] == "bullish" and daily["signal"] == "bullish":
            recommended_action = "buy on pullback"
        elif monthly["signal"] == "bullish" and weekly["signal"] in {"bullish", "netral"}:
            recommended_action = "akumulasi bertahap"
        else:
            recommended_action = "pantau"

        reasons = [
            f"Daily {daily['signal']} ({daily['confidence']}, {daily['probability_up']:.0%} naik).",
            f"Weekly {weekly['signal']} ({weekly['confidence']}, {weekly['expected_return']:.1%} expected return).",
            f"Monthly {monthly['signal']} ({monthly['confidence']}, regime {monthly['regime']['label']}).",
        ]

        if latest.get("sentiment"):
            reasons.append(f"Sentimen {latest['sentiment']['label']} dengan {latest['sentiment']['headline_count']} headline.")
        if latest.get("macro"):
            reasons.append(f"Macro risk budget: {latest['macro']['risk_budget']}.")
        reasons.append(latest_scenario.get("playbook") or "Gunakan entry dekat zona dan disiplin stop loss.")

        if bullish_count >= 2:
            rank_score = avg_probability + avg_expected_return + confidence_score + 0.05
        elif bearish_count >= 2:
            rank_score = avg_probability + avg_expected_return - 0.12
        else:
            rank_score = avg_probability + avg_expected_return + confidence_score

        items.append(
            {
                "ticker": symbol,
                "rank_score": round(rank_score, 4),
                "recommended_action": recommended_action,
                "entry_zone_low": round(entry_low, 2),
                "entry_zone_high": round(entry_high, 2),
                "target_price": round(target_price, 2),
                "stop_loss": round(stop_loss, 2),
                "reasons": reasons,
                "daily": {
                    "label": "harian",
                    "horizon_days": daily_horizon,
                    "signal": daily["signal"],
                    "probability_up": daily["probability_up"],
                    "confidence": daily["confidence"],
                    "expected_return": daily["expected_return"],
                    "risk_label": daily["risk_label"],
                    "summary": daily["scenario"]["playbook"],
                },
                "weekly": {
                    "label": "mingguan",
                    "horizon_days": weekly_horizon,
                    "signal": weekly["signal"],
                    "probability_up": weekly["probability_up"],
                    "confidence": weekly["confidence"],
                    "expected_return": weekly["expected_return"],
                    "risk_label": weekly["risk_label"],
                    "summary": weekly["scenario"]["playbook"],
                },
                "monthly": {
                    "label": "bulanan",
                    "horizon_days": monthly_horizon,
                    "signal": monthly["signal"],
                    "probability_up": monthly["probability_up"],
                    "confidence": monthly["confidence"],
                    "expected_return": monthly["expected_return"],
                    "risk_label": monthly["risk_label"],
                    "summary": monthly["scenario"]["playbook"],
                },
                "latest_prediction": latest,
            }
        )

    items.sort(key=lambda item: (item["rank_score"], item["latest_prediction"]["probability_up"]), reverse=True)
    return {
        "market": market,
        "universe_size": len(universe),
        "scanned_size": len(items),
        "items": items,
    }


def _safe_float(value: object, fallback: float = 0.0) -> float:
    try:
        if value is None or pd.isna(value):
            return fallback
        return float(value)
    except Exception:
        return fallback


def _score_label(final_score: int, risk_reward: float) -> str:
    if final_score >= 82 and risk_reward >= 1.8:
        return "Strong Buy Candidate"
    if final_score >= 70 and risk_reward >= 1.5:
        return "Strong Watch"
    if final_score >= 58:
        return "Watch"
    if final_score >= 45:
        return "Neutral"
    return "Avoid"


def _horizon_days_from_label(horizon: str) -> int:
    normalized = horizon.strip().lower()
    if normalized in {"daily", "harian"}:
        return 5
    if normalized in {"monthly", "bulanan"}:
        return 60
    return 20


def _round_price(value: float, market: str) -> float:
    if market == "id":
        if value >= 5000:
            step = 25
        elif value >= 2000:
            step = 10
        elif value >= 500:
            step = 5
        else:
            step = 1
        return float(round(value / step) * step)
    return round(value, 2)


def _pct_change(close: pd.Series, days: int) -> float:
    if len(close) <= days:
        return 0.0
    previous = _safe_float(close.iloc[-days - 1])
    latest = _safe_float(close.iloc[-1])
    if previous <= 0:
        return 0.0
    return latest / previous - 1


def _max_drawdown(close: pd.Series) -> float:
    values = close.astype(float)
    peak = values.cummax()
    drawdown = values / peak - 1
    return float(drawdown.min()) if len(drawdown) else 0.0


async def build_idx_recommendation(
    session: AsyncSession,
    ticker: str,
    horizon: str = "weekly",
    market: str = "id",
    market_data_providers: list | None = None,
) -> dict:
    symbol = normalize_backend_ticker(ticker, market)
    horizon_days = _horizon_days_from_label(horizon)
    df = await load_price_frame(session, symbol, max(300, horizon_days * 8))
    if df.empty or len(df) < 60:
        raise ValueError(f"Data OHLCV belum cukup untuk {symbol}.")

    from backend.app.services.bandarmology_engine import build_bandarmology, build_live_bandarmology, enrich_ohlcv

    enriched = enrich_ohlcv(df).dropna(subset=["close"]).reset_index(drop=True)
    latest = enriched.iloc[-1]
    close = enriched["close"].astype(float)
    volume = enriched["volume"].astype(float)
    latest_close = _safe_float(latest.close)
    ma20 = _safe_float(latest.ma20, latest_close)
    ma50 = _safe_float(latest.ma50, latest_close)
    ma200 = _safe_float(latest.ma200, latest_close)
    support = _safe_float(enriched["low"].tail(30).min(), latest_close * 0.96)
    resistance = _safe_float(enriched["high"].tail(30).max(), latest_close * 1.04)
    volume_5 = _safe_float(volume.tail(5).mean())
    volume_20 = _safe_float(volume.tail(20).mean())
    volume_ratio = volume_5 / volume_20 if volume_20 > 0 else 1.0

    selected_provider = None
    for provider in market_data_providers or []:
        if getattr(provider, "endpoint", "") and getattr(provider, "api_key", ""):
            selected_provider = provider
            break
    bandarmology = (
        build_live_bandarmology(enriched, symbol, selected_provider, 30)
        if selected_provider
        else build_bandarmology(enriched, symbol)
    )

    benchmark_symbol = "^JKSE" if market == "id" else "SPY"
    relative_strength = 0.0
    macro_available = False
    try:
        benchmark_df = await load_price_frame(session, benchmark_symbol, 120)
        stock_return = _pct_change(close, horizon_days)
        benchmark_return = _pct_change(benchmark_df["close"].astype(float), horizon_days)
        relative_strength = stock_return - benchmark_return
        macro_available = True
    except Exception:
        stock_return = _pct_change(close, horizon_days)

    technical_score = 0
    technical_score += 8 if ma20 > ma50 else 0
    technical_score += 5 if ma50 > ma200 else 0
    technical_score += 5 if latest_close > ma20 else 0
    technical_score += 4 if stock_return > 0 else 0
    technical_score += 3 if resistance > latest_close else 0
    technical_score = min(25, technical_score)

    volume_score = min(15, max(0, round((volume_ratio - 0.8) / 0.8 * 15)))
    relative_strength_score = min(15, max(0, round((relative_strength + 0.04) / 0.12 * 15)))
    smart_money = _safe_float(bandarmology.get("smart_money_score"))
    bandar_score = min(20, max(0, round((smart_money + 1) / 2 * 20)))
    if bandarmology.get("verdict") == "akumulasi":
        bandar_score = min(20, bandar_score + 3)
    if bandarmology.get("verdict") == "distribusi":
        bandar_score = max(0, bandar_score - 5)

    atr_proxy = _safe_float((enriched["high"].astype(float) - enriched["low"].astype(float)).tail(14).mean(), latest_close * 0.025)
    stop_loss = min(support, latest_close - atr_proxy * 1.2)
    if stop_loss >= latest_close:
        stop_loss = latest_close * 0.97
    target_1 = max(resistance, latest_close + atr_proxy * 1.8)
    target_2 = max(target_1 * 1.03, latest_close + atr_proxy * 3.0)
    entry_low = max(stop_loss * 1.01, latest_close - atr_proxy * 0.8)
    entry_high = min(latest_close * 1.01, latest_close + atr_proxy * 0.2)
    risk_per_share = max(entry_high - stop_loss, 0.01)
    reward_per_share = max(target_1 - entry_high, 0.01)
    risk_reward = round(reward_per_share / risk_per_share, 2)
    risk_reward_score = min(10, max(0, round(risk_reward / 3 * 10)))
    macro_score = 5 if macro_available and relative_strength >= -0.02 else 2 if macro_available else 0

    score_breakdown = {
        "technical": int(technical_score),
        "volume": int(volume_score),
        "relative_strength": int(relative_strength_score),
        "bandarmology": int(bandar_score),
        "risk_reward": int(risk_reward_score),
        "macro": int(macro_score),
    }
    final_score = int(min(100, sum(score_breakdown.values())))
    confidence = round(min(0.95, max(0.35, final_score / 100 * 0.75 + (0.08 if len(enriched) >= 200 else 0))), 2)

    reasons: list[str] = []
    if ma20 > ma50:
        reasons.append("Trend MA20 berada di atas MA50.")
    if latest_close > ma20:
        reasons.append("Harga terakhir bertahan di atas MA20.")
    if volume_ratio >= 1.12:
        reasons.append("Volume 5 hari terakhir meningkat dibanding rata-rata 20 hari.")
    if relative_strength > 0:
        reasons.append("Relative strength mengalahkan benchmark pasar.")
    if bandarmology.get("verdict") == "akumulasi":
        reasons.append("Bandarmology menunjukkan akumulasi.")
    elif smart_money > 0:
        reasons.append("Smart money proxy masih positif.")
    if risk_reward >= 1.5:
        reasons.append(f"Risk/reward masih layak di sekitar {risk_reward}x.")
    if not reasons:
        reasons.append("Belum ada sinyal dominan; ticker masuk mode pantau.")

    risks: list[str] = []
    risks.append(f"Support {round(stop_loss, 2)} tidak boleh ditembus.")
    if latest_close >= resistance * 0.98:
        risks.append("Harga sudah dekat resistance, rawan pullback pendek.")
    if volume_ratio < 0.9:
        risks.append("Volume belum mendukung konfirmasi kuat.")
    if bandarmology.get("verdict") == "distribusi":
        risks.append("Bandarmology mendeteksi tekanan distribusi.")
    if not macro_available:
        risks.append("Data benchmark/makro belum lengkap, relative strength memakai estimasi terbatas.")

    signal = _score_label(final_score, risk_reward)
    as_of = latest.date.isoformat() if hasattr(latest.date, "isoformat") else str(latest.date)
    return {
        "symbol": symbol,
        "market": market,
        "horizon": horizon,
        "final_score": final_score,
        "signal": signal,
        "confidence": confidence,
        "last_price": _round_price(latest_close, market),
        "entry_zone": [_round_price(entry_low, market), _round_price(entry_high, market)],
        "target_1": _round_price(target_1, market),
        "target_2": _round_price(target_2, market),
        "stop_loss": _round_price(stop_loss, market),
        "risk_reward": risk_reward,
        "score_breakdown": score_breakdown,
        "main_reasons": reasons[:6],
        "main_risks": risks[:5],
        "price_context": {
            "last_price": _round_price(latest_close, market),
            "ma20": _round_price(ma20, market),
            "ma50": _round_price(ma50, market),
            "ma200": _round_price(ma200, market),
            "support": _round_price(support, market),
            "resistance": _round_price(resistance, market),
            "volume_ratio_5d": round(volume_ratio, 2),
            "relative_strength": round(relative_strength, 4),
        },
        "data_quality": {
            "ohlcv_available": True,
            "bandarmology_available": bool(bandarmology),
            "macro_available": macro_available,
            "fundamental_available": False,
        },
        "validation": {
            "backtest_win_rate": None,
            "sample_size": int(len(enriched)),
            "max_drawdown": round(_max_drawdown(close.tail(120)), 4),
            "last_updated": as_of,
        },
    }


async def get_market_rows(session: AsyncSession, symbol: str) -> list[MarketPrice]:
    result = await session.execute(
        select(MarketPrice)
        .where(MarketPrice.symbol == symbol)
        .order_by(MarketPrice.date)
    )
    return list(result.scalars().all())
