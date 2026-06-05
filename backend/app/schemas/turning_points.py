from pydantic import BaseModel, Field
from typing import List


class TurningPointResponse(BaseModel):
    date: str = Field(..., description="Turning point date in YYYY-MM-DD format")
    type: str = Field(..., description="TOP or BOTTOM")
    strength: int = Field(..., ge=0, le=100, description="Strength 0-100")


class TurningPointsResponse(BaseModel):
    ticker: str = Field(..., description="Market ticker")
    lookback_days: int = Field(..., description="Number of days analyzed")
    turning_points: List[TurningPointResponse] = Field(
        ..., description="List of detected turning points"
    )
    total_detected: int = Field(..., description="Total number of turning points")
