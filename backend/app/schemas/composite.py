from pydantic import BaseModel, Field


class CycleComboInput(BaseModel):
    planet_a: str = Field(..., description="First planet (Sun, Moon, Mercury, Venus, Mars, Jupiter, Saturn)")
    planet_b: str = Field(..., description="Second planet")
    weight: float = Field(1.0, ge=0.1, le=10.0, description="Weight for this cycle combination")


class CompositeResponse(BaseModel):
    date: str
    value: float
    smoothed_7d: float | None = None
    smoothed_30d: float | None = None
    smoothed_60d: float | None = None
    projected: bool = False


class CompositeRequestBody(BaseModel):
    combinations: list[CycleComboInput]
    start_date: str = Field(..., description="Start date in YYYY-MM-DD format")
    end_date: str = Field(..., description="End date in YYYY-MM-DD format")
    smoothing_windows: list[int] = Field(default=[7, 30, 60], description="Rolling windows for smoothing")
    project_days: int = Field(0, ge=0, le=365, description="Number of days to project into the future")
