from datetime import date, timedelta
from typing import Any
import math
import numpy as np
import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.models import AstroMeasurement
from backend.app.services.ephemeris_service import DEFAULT_PLANETS


class CycleCombination:
    def __init__(self, planet_a: str, planet_b: str, weight: float = 1.0):
        if planet_a not in DEFAULT_PLANETS or planet_b not in DEFAULT_PLANETS:
            raise ValueError(f"Invalid planet. Must be one of: {', '.join(DEFAULT_PLANETS)}")
        if planet_a == planet_b:
            raise ValueError("Planets must be different")
        if weight <= 0:
            raise ValueError("Weight must be positive")
        self.planet_a = planet_a
        self.planet_b = planet_b
        self.weight = weight


async def calculate_composite_cycle(
    session: AsyncSession,
    combinations: list[CycleCombination],
    start_date: date,
    end_date: date,
) -> list[dict[str, Any]]:
    if not combinations:
        raise ValueError("At least one combination is required")
    if end_date < start_date:
        raise ValueError("end_date must be after start_date")

    query = (
        select(AstroMeasurement)
        .where(AstroMeasurement.date >= start_date)
        .where(AstroMeasurement.date <= end_date)
        .order_by(AstroMeasurement.date)
    )
    result = await session.execute(query)
    measurements = result.scalars().all()

    if not measurements:
        return []

    measurements_by_date = {}
    for m in measurements:
        if m.date not in measurements_by_date:
            measurements_by_date[m.date] = {}
        measurements_by_date[m.date][m.body] = m.longitude

    composite_points = []
    for curr_date in sorted(measurements_by_date.keys()):
        body_map = measurements_by_date[curr_date]
        weighted_sum = 0.0
        total_weight = 0.0

        for combo in combinations:
            if combo.planet_a not in body_map or combo.planet_b not in body_map:
                continue
            lon_a = body_map[combo.planet_a]
            lon_b = body_map[combo.planet_b]
            angle_diff = lon_a - lon_b
            cycle_value = math.cos(math.radians(angle_diff))
            weighted_sum += combo.weight * cycle_value
            total_weight += combo.weight

        if total_weight > 0:
            normalized_value = weighted_sum / total_weight
            composite_points.append({"date": curr_date.isoformat(), "value": float(normalized_value)})

    return composite_points


def apply_smoothing(data: list[dict[str, Any]], window: int) -> list[dict[str, Any]]:
    if not data:
        return []
    if window <= 0:
        raise ValueError("Window must be positive")

    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")
    df["smoothed"] = df["value"].rolling(window=window, min_periods=1, center=False).mean()

    result = []
    for _, row in df.iterrows():
        result.append({
            "date": row["date"].strftime("%Y-%m-%d"),
            "value": float(row["value"]),
            "smoothed": float(row["smoothed"]),
        })
    return result


def project_future_values(data: list[dict[str, Any]], days_ahead: int) -> list[dict[str, Any]]:
    if not data or days_ahead <= 0:
        return []

    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")

    if len(df) < 2:
        return []

    df["value_numeric"] = df["value"]
    x = np.arange(len(df)).reshape(-1, 1)
    y = df["value_numeric"].values

    try:
        coeffs = np.polyfit(x.flatten(), y, 2)
        poly = np.poly1d(coeffs)
    except Exception:
        return []

    projections = []
    last_date = df["date"].iloc[-1]

    for i in range(1, days_ahead + 1):
        future_date = last_date + timedelta(days=i)
        x_pred = len(df) + i - 1
        y_pred = float(poly(x_pred))
        y_pred = max(-1.0, min(1.0, y_pred))
        projections.append({"date": future_date.strftime("%Y-%m-%d"), "value": y_pred})

    return projections
