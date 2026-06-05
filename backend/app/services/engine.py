from datetime import date
import numpy as np
import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.models import AstroMeasurement, MarketPrice
from backend.app.schemas.models import ForecastResponse, TurningPointRead


def compute_angle_series(df: pd.DataFrame, body_a: str, body_b: str) -> pd.Series:
    merged = df.pivot(index="date", columns="body", values="longitude")
    delta = np.radians((merged[body_a] - merged[body_b]).dropna())
    return np.cos(delta)


def smooth_series(series: pd.Series, window: int = 30) -> pd.Series:
    return series.rolling(window=window, min_periods=1, center=False).mean()


async def build_composite_forecast(session: AsyncSession, symbol: str) -> list[ForecastResponse]:
    price_result = await session.execute(select(MarketPrice).where(MarketPrice.symbol == symbol).order_by(MarketPrice.date))
    prices = pd.DataFrame([p.__dict__ for p in price_result.scalars().all()])
    if prices.empty:
        return []
    astro_result = await session.execute(select(AstroMeasurement).order_by(AstroMeasurement.date))
    astro = pd.DataFrame([a.__dict__ for a in astro_result.scalars().all()])
    if astro.empty:
        return []

    bodies = ["Sun", "Venus", "Jupiter", "Moon", "Saturn"]
    combos = [("Sun", "Venus"), ("Sun", "Jupiter"), ("Moon", "Saturn")]
    signal_series = pd.DataFrame({
        f"{a}-{b}": compute_angle_series(astro, a, b)
        for a, b in combos
    })
    composite = signal_series.mean(axis=1)
    smoothed = smooth_series(composite, window=30)
    forecast_points = []
    last_date = prices["date"].max()
    for offset, value in enumerate(smoothed.tail(10), start=1):
        forecast_points.append(
            ForecastResponse(
                symbol=symbol,
                forecast_date=last_date,
                projected_value=float(value),
                signal="bullish" if value > 0 else "bearish",
            )
        )
    return forecast_points


async def detect_turning_points(session: AsyncSession, symbol: str) -> TurningPointRead | None:
    price_result = await session.execute(select(MarketPrice).where(MarketPrice.symbol == symbol).order_by(MarketPrice.date))
    prices = pd.DataFrame([p.__dict__ for p in price_result.scalars().all()])
    if prices.empty:
        return None
    prices = prices.set_index("date").sort_index()
    prices["returns"] = prices["close"].pct_change()
    tops = prices["returns"].nlargest(3).index
    bottoms = prices["returns"].nsmallest(3).index
    return TurningPointRead(
        symbol=symbol,
        top=tops[-1].date() if len(tops) else prices.index.max().date(),
        bottom=bottoms[-1].date() if len(bottoms) else prices.index.min().date(),
        explanation="Basic turning point estimation based on recent return extremes.",
    )
