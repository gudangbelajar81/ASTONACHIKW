from datetime import date
from typing import Optional
from pydantic import BaseModel, ConfigDict


class AstroMeasurementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    date: date
    body: str
    longitude: float
    value: Optional[float]


class MarketPriceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    date: date
    symbol: str
    close: float
    open: Optional[float]
    high: Optional[float]
    low: Optional[float]
    volume: Optional[float]


class CycleCandidateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    body_a: str
    body_b: str
    score: Optional[float]
    details: Optional[str]


class ScanResult(BaseModel):
    symbol: str
    candidates: list[CycleCandidateRead]


class ForecastResponse(BaseModel):
    symbol: str
    forecast_date: date
    projected_value: float
    signal: str


class TurningPointRead(BaseModel):
    symbol: str
    top: date
    bottom: date
    explanation: Optional[str]
