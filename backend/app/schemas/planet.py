from datetime import date
from pydantic import BaseModel, ConfigDict


class PlanetPositions(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "date": "2025-01-01",
                "sun": 123.45,
                "moon": 210.33,
                "mercury": 87.22,
                "venus": 98.23,
                "mars": 132.41,
                "jupiter": 212.11,
                "saturn": 45.19,
            }
        }
    )

    date: date
    sun: float
    moon: float
    mercury: float
    venus: float
    mars: float
    jupiter: float
    saturn: float
