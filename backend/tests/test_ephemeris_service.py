from datetime import date
import pytest
from backend.app.services import ephemeris_service


def test_get_body_longitude(monkeypatch):
    def fake_set_ephe_path(path):
        assert path == ephemeris_service.settings.SWISSEPH_PATH

    def fake_calc_ut(jd, body_code):
        assert body_code == ephemeris_service.swe.SUN
        return [123.45, 0.0, 0.0, 0.0]

    monkeypatch.setattr(ephemeris_service.swe, "set_ephe_path", fake_set_ephe_path)
    monkeypatch.setattr(ephemeris_service.swe, "calc_ut", fake_calc_ut)

    result = ephemeris_service.get_body_longitude("Sun", date(2025, 1, 1))
    assert result == 123.45


def test_daily_planetary_positions(monkeypatch):
    def fake_get_body_longitude(body_name, target_date):
        return float(len(body_name))

    monkeypatch.setattr(ephemeris_service, "get_body_longitude", fake_get_body_longitude)

    positions = ephemeris_service.daily_planetary_positions(date(2025, 1, 1), date(2025, 1, 2))
    assert len(positions) == 2
    assert positions[0]["date"] == date(2025, 1, 1)
    assert positions[0]["sun"] == float(len("Sun"))
    assert positions[1]["venus"] == float(len("Venus"))


def test_daily_planetary_positions_invalid_range():
    with pytest.raises(ValueError):
        ephemeris_service.daily_planetary_positions(date(2025, 1, 5), date(2025, 1, 1))
