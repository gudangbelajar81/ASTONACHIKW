from datetime import date, datetime, timedelta
from typing import Any
import swisseph as swe
from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.config import settings
from backend.app.db.models import AstroMeasurement

PLANET_CODES = {
    "Sun": swe.SUN,
    "Moon": swe.MOON,
    "Mercury": swe.MERCURY,
    "Venus": swe.VENUS,
    "Mars": swe.MARS,
    "Jupiter": swe.JUPITER,
    "Saturn": swe.SATURN,
}

PLANET_KEYS = {
    "Sun": "sun",
    "Moon": "moon",
    "Mercury": "mercury",
    "Venus": "venus",
    "Mars": "mars",
    "Jupiter": "jupiter",
    "Saturn": "saturn",
}

DEFAULT_PLANETS = list(PLANET_CODES.keys())


def load_ephemeris() -> None:
    swe.set_ephe_path(settings.SWISSEPH_PATH)


def get_body_longitude(body_name: str, target_date: date) -> float:
    if body_name not in PLANET_CODES:
        raise ValueError(f"Unsupported body: {body_name}")
    load_ephemeris()
    dt = datetime(target_date.year, target_date.month, target_date.day, 0, 0)
    jd = swe.julday(dt.year, dt.month, dt.day, dt.hour + dt.minute / 60)
    position = swe.calc_ut(jd, PLANET_CODES[body_name])
    return float(position[0])


def daily_planetary_positions(start_date: date, end_date: date) -> list[dict[str, Any]]:
    if end_date < start_date:
        raise ValueError("end_date must be after start_date")

    output = []
    current = start_date
    while current <= end_date:
        row = {"date": current}
        for body in DEFAULT_PLANETS:
            row[PLANET_KEYS[body]] = get_body_longitude(body, current)
        output.append(row)
        current += timedelta(days=1)
    return output


async def upsert_planetary_positions(session: AsyncSession, start_date: date, end_date: date) -> None:
    measurements = []
    for current in [start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1)]:
        for body in DEFAULT_PLANETS:
            longitude = get_body_longitude(body, current)
            measurements.append(
                {
                    "date": current,
                    "body": body,
                    "longitude": longitude,
                }
            )

    if not measurements:
        return

    stmt = insert(AstroMeasurement)
    stmt = stmt.on_conflict_do_update(
        index_elements=["date", "body"],
        set_={"longitude": stmt.excluded.longitude},
    )

    await session.execute(stmt, measurements)
    await session.commit()


async def get_planetary_positions(session: AsyncSession, target_date: date | None = None) -> dict[str, Any] | None:
    if target_date is None:
        latest_date_result = await session.execute(select(func.max(AstroMeasurement.date)))
        target_date = latest_date_result.scalar_one_or_none()
        if target_date is None:
            return None

    query = select(AstroMeasurement).where(AstroMeasurement.date == target_date)
    result = await session.execute(query)
    rows = result.scalars().all()
    if not rows:
        return None

    response = {"date": target_date.isoformat()}
    for row in rows:
        key = PLANET_KEYS.get(row.body)
        if key:
            response[key] = float(row.longitude)
    if len(response) != len(PLANET_KEYS) + 1:
        return None
    return response
