from datetime import date
import math
import pytest
from backend.app.services import cycle_engine


def test_calculate_cycle_valid(monkeypatch):
    async def fake_execute(query):
        from unittest.mock import Mock
        mock = Mock()
        m1 = Mock()
        m1.date = date(2025, 1, 1)
        m1.body = "Sun"
        m1.longitude = 100.0
        m2 = Mock()
        m2.date = date(2025, 1, 1)
        m2.body = "Moon"
        m2.longitude = 50.0
        mock.scalars.return_value.all.return_value = [m1, m2]
        return mock

    class FakeSession:
        async def execute(self, query):
            return await fake_execute(query)

    session = FakeSession()
    result = cycle_engine.calculate_cycle(
        session, "Sun", "Moon", date(2025, 1, 1), date(2025, 1, 1)
    )

    assert isinstance(result, dict)


def test_calculate_cycle_invalid_planet():
    with pytest.raises(ValueError, match="Invalid planet"):
        cycle_engine.calculate_cycle(None, "InvalidPlanet", "Sun", date(2025, 1, 1), date(2025, 1, 1))


def test_calculate_cycle_same_planet():
    with pytest.raises(ValueError, match="must be different"):
        cycle_engine.calculate_cycle(None, "Sun", "Sun", date(2025, 1, 1), date(2025, 1, 1))


def test_calculate_cycle_invalid_range():
    with pytest.raises(ValueError, match="end_date must be after start_date"):
        cycle_engine.calculate_cycle(None, "Sun", "Moon", date(2025, 1, 5), date(2025, 1, 1))


def test_normalize_cycle():
    assert cycle_engine.normalize_cycle(0.5) == 0.5
    assert cycle_engine.normalize_cycle(1.5) == 1.0
    assert cycle_engine.normalize_cycle(-1.5) == -1.0
    assert cycle_engine.normalize_cycle(math.cos(math.radians(45))) == pytest.approx(0.7071, rel=0.001)
