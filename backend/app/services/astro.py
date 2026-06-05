from datetime import date, datetime, timedelta
import swisseph as swe
from backend.app.core.config import settings
import pandas as pd


PLANET_CODES = {
    "Sun": swe.SUN,
    "Moon": swe.MOON,
    "Mercury": swe.MERCURY,
    "Venus": swe.VENUS,
    "Mars": swe.MARS,
    "Jupiter": swe.JUPITER,
    "Saturn": swe.SATURN,
    "Uranus": swe.URANUS,
    "Neptune": swe.NEPTUNE,
    "Pluto": swe.PLUTO,
}


def load_ephemeris():
    swe.set_ephe_path(settings.SWISSEPH_PATH)


def get_body_longitude(body_name: str, target_date: date) -> float:
    if body_name not in PLANET_CODES:
        raise ValueError(f"Unsupported body: {body_name}")
    load_ephemeris()
    dt = datetime(target_date.year, target_date.month, target_date.day, 0, 0)
    jd = swe.julday(dt.year, dt.month, dt.day, dt.hour + dt.minute / 60)
    position = swe.calc_ut(jd, PLANET_CODES[body_name])
    return float(position[0])


def get_daily_longitudes(body_name: str, start_date: date, end_date: date) -> pd.DataFrame:
    days = (end_date - start_date).days + 1
    values = []
    for offset in range(days):
        dt = start_date + timedelta(days=offset)
        lon = get_body_longitude(body_name, dt)
        values.append({"date": dt, "body": body_name, "longitude": lon})
    return pd.DataFrame(values)
