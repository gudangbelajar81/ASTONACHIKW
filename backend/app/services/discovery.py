import itertools
import numpy as np
import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.models import AstroMeasurement, CycleCandidate, MarketPrice
from backend.app.services.market import get_market_prices


async def scan_best_cycles(session: AsyncSession, symbol: str) -> list[CycleCandidate]:
    astro_result = await session.execute(select(AstroMeasurement).order_by(AstroMeasurement.date))
    astro = pd.DataFrame([a.__dict__ for a in astro_result.scalars().all()])
    if astro.empty:
        return []

    prices = await get_market_prices(session, symbol)
    price_df = pd.DataFrame([p.__dict__ for p in prices])
    if price_df.empty:
        return []
    price_df = price_df[["date", "close"]].dropna().set_index("date")

    bodies = astro["body"].unique().tolist()
    candidate_scores = []
    for a, b in itertools.combinations(bodies, 2):
        score = compute_cycle_correlation(astro, price_df, a, b)
        candidate_scores.append((a, b, score))

    candidate_scores.sort(key=lambda item: item[2], reverse=True)
    best = []
    for a, b, score in candidate_scores[:10]:
        best.append(
            CycleCandidate(
                name=f"{a}-{b}",
                body_a=a,
                body_b=b,
                score=float(score),
                details=f"Correlation score against {symbol}: {score:.4f}",
            )
        )
    return best


def compute_cycle_correlation(astro: pd.DataFrame, price_df: pd.DataFrame, body_a: str, body_b: str) -> float:
    pivot = astro.pivot(index="date", columns="body", values="longitude").dropna()
    if body_a not in pivot.columns or body_b not in pivot.columns:
        return 0.0

    signal = np.cos(np.radians(pivot[body_a] - pivot[body_b]))
    joined = signal.to_frame(name="signal").join(price_df, how="inner")
    if joined.shape[0] < 10:
        return 0.0

    correlation = np.corrcoef(joined["signal"].values, joined["close"].values)[0, 1]
    return float(np.abs(correlation)) if not np.isnan(correlation) else 0.0
