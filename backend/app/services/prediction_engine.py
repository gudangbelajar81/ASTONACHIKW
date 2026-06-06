from dataclasses import dataclass
from datetime import date, timedelta
import math

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import MarketPrice, ModelWeightProfile, PredictionSnapshot
from backend.app.services.composite_engine import CycleCombination, calculate_composite_cycle
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


def sigmoid(value: float) -> float:
    return 1 / (1 + math.exp(-value))


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

    score = sum(factor.contribution for factor in factors)
    probability_up = sigmoid(score * 2.2)
    expected_return = (probability_up - 0.5) * 0.16

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

    risk_label = "tinggi" if volatility_20 >= 0.035 else "sedang" if volatility_20 >= 0.02 else "rendah"
    return factors, probability_up, expected_return, signal, confidence, risk_label


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


async def build_prediction(session: AsyncSession, ticker: str, horizon_days: int = 30) -> dict:
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


async def get_market_rows(session: AsyncSession, symbol: str) -> list[MarketPrice]:
    result = await session.execute(
        select(MarketPrice)
        .where(MarketPrice.symbol == symbol)
        .order_by(MarketPrice.date)
    )
    return list(result.scalars().all())
