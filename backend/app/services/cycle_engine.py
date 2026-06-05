from datetime import date, timedelta
from typing import Any
import math
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.models import AstroMeasurement
from backend.app.services.ephemeris_service import PLANET_KEYS, DEFAULT_PLANETS


async def calculate_cycle(
    session: AsyncSession,
    planet_a: str,
    planet_b: str,
    start_date: date,
    end_date: date,
) -> list[dict[str, Any]]:
    if planet_a not in DEFAULT_PLANETS or planet_b not in DEFAULT_PLANETS:
        raise ValueError(f"Invalid planet. Must be one of: {', '.join(DEFAULT_PLANETS)}")

    if planet_a == planet_b:
        raise ValueError("planet_a and planet_b must be different")

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

    cycles = []
    for curr_date in sorted(measurements_by_date.keys()):
        body_map = measurements_by_date[curr_date]
        if planet_a not in body_map or planet_b not in body_map:
            continue

        lon_a = body_map[planet_a]
        lon_b = body_map[planet_b]
        angle_diff = lon_a - lon_b
        cycle_value = math.cos(math.radians(angle_diff))
        cycles.append({"date": curr_date.isoformat(), "value": float(cycle_value)})

    return cycles


def normalize_cycle(value: float) -> float:
    return max(-1.0, min(1.0, value))
