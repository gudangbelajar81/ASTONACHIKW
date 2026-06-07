from datetime import date, timedelta
from typing import Any
import itertools
import math
import numpy as np
import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.models import AstroMeasurement
from backend.app.services.ephemeris_service import DEFAULT_PLANETS
from backend.app.services.market import fetch_market_data as fetch_ohlcv_frame


class ScanResult:
    def __init__(
        self,
        planet_a: str,
        planet_b: str,
        correlation: float,
        lag_days: int,
        accuracy: float,
        sample_count: int,
    ):
        self.cycle = f"{planet_a}-{planet_b}"
        self.planet_a = planet_a
        self.planet_b = planet_b
        self.correlation = correlation
        self.lag_days = lag_days
        self.accuracy = accuracy
        self.sample_count = sample_count
        self.score = self._calculate_score()

    def _calculate_score(self) -> float:
        corr_weight = abs(self.correlation) * 0.6
        accuracy_weight = self.accuracy * 0.4
        return corr_weight + accuracy_weight

    def to_dict(self) -> dict[str, Any]:
        return {
            "cycle": self.cycle,
            "correlation": round(self.correlation, 4),
            "lag_days": self.lag_days,
            "accuracy": round(self.accuracy, 4),
            "score": round(self.score, 4),
            "sample_count": self.sample_count,
        }


async def scan_cycles(
    session: AsyncSession,
    ticker: str,
    lookback_years: int = 3,
) -> list[dict[str, Any]]:
    if lookback_years < 1 or lookback_years > 20:
        raise ValueError("lookback_years must be between 1 and 20")

    end_date = date.today()
    start_date = end_date - timedelta(days=365 * lookback_years)

    market_data = fetch_market_data(ticker, start_date, end_date)
    if market_data is None or len(market_data) < 30:
        raise ValueError(f"Insufficient market data for {ticker}")

    query = (
        select(AstroMeasurement)
        .where(AstroMeasurement.date >= start_date)
        .where(AstroMeasurement.date <= end_date)
        .order_by(AstroMeasurement.date)
    )
    result = await session.execute(query)
    measurements = result.scalars().all()

    if not measurements:
        raise ValueError("No astronomical data available for the date range")

    measurements_by_date = {}
    for m in measurements:
        if m.date not in measurements_by_date:
            measurements_by_date[m.date] = {}
        measurements_by_date[m.date][m.body] = m.longitude

    scan_results = []
    combinations = list(itertools.combinations(DEFAULT_PLANETS, 2))

    for planet_a, planet_b in combinations:
        cycle_data = build_cycle_series(measurements_by_date, planet_a, planet_b, start_date, end_date)
        if not cycle_data or len(cycle_data) < 30:
            continue

        correlation, lag_days, accuracy = calculate_metrics(cycle_data, market_data)
        result = ScanResult(planet_a, planet_b, correlation, lag_days, accuracy, len(cycle_data))
        scan_results.append(result)

    scan_results.sort(key=lambda x: x.score, reverse=True)
    return [r.to_dict() for r in scan_results[:20]]


def build_cycle_series(
    measurements_by_date: dict,
    planet_a: str,
    planet_b: str,
    start_date: date,
    end_date: date,
) -> list[dict[str, Any]]:
    cycle_points = []
    current = start_date
    while current <= end_date:
        if current in measurements_by_date:
            body_map = measurements_by_date[current]
            if planet_a in body_map and planet_b in body_map:
                lon_a = body_map[planet_a]
                lon_b = body_map[planet_b]
                angle_diff = lon_a - lon_b
                cycle_value = math.cos(math.radians(angle_diff))
                cycle_points.append({"date": current, "cycle": cycle_value})
        current += timedelta(days=1)
    return cycle_points


def fetch_market_data(
    ticker: str,
    start_date: date,
    end_date: date,
) -> list[dict[str, Any]] | None:
    try:
        data = fetch_ohlcv_frame(ticker, start_date, end_date)
        if data.empty:
            return None
        data = data.copy()
        data["returns"] = data["close"].pct_change()
        data["direction"] = (data["returns"] > 0).astype(int)
        return [
            {
                "date": pd.Timestamp(row["date"]).date(),
                "close": float(row["close"]),
                "returns": float(row["returns"]) if pd.notna(row["returns"]) else 0.0,
                "direction": int(row["direction"]),
            }
            for _, row in data.iterrows()
        ]
    except Exception:
        return None


def calculate_metrics(
    cycle_data: list[dict[str, Any]],
    market_data: list[dict[str, Any]],
) -> tuple[float, int, float]:
    cycle_df = pd.DataFrame(cycle_data)
    market_df = pd.DataFrame(market_data)

    joined = cycle_df.merge(market_df, on="date", how="inner")
    if len(joined) < 20:
        return 0.0, 0, 0.0

    cycle_values = joined["cycle"].values
    market_returns = joined["returns"].values

    correlation = 0.0
    if len(cycle_values) > 1 and len(market_returns) > 1:
        corr_matrix = np.corrcoef(cycle_values, market_returns)
        correlation = float(corr_matrix[0, 1]) if not np.isnan(corr_matrix[0, 1]) else 0.0

    best_lag = 0
    best_accuracy = 0.5

    for lag in range(0, min(21, len(joined) // 2)):
        cycle_shifted = cycle_values[:-lag] if lag > 0 else cycle_values
        market_dir = joined["direction"].values[lag:]

        if len(cycle_shifted) != len(market_dir):
            continue

        predictions = (cycle_shifted > 0).astype(int)
        accuracy = np.mean(predictions == market_dir)

        if accuracy > best_accuracy:
            best_accuracy = accuracy
            best_lag = lag

    return correlation, best_lag, best_accuracy
