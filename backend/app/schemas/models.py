from datetime import date
from typing import Optional
from pydantic import BaseModel


class AstroMeasurementRead(BaseModel):
    date: date
    body: str
    longitude: float
    value: Optional[float]

    class Config:
        orm_mode = True


class MarketPriceRead(BaseModel):
    date: date
    symbol: str
    close: float
    open: Optional[float]
    high: Optional[float]
    low: Optional[float]
    volume: Optional[float]

    class Config:
        orm_mode = True


class CycleCandidateRead(BaseModel):
    name: str
    body_a: str
    body_b: str
    score: Optional[float]
    details: Optional[str]

    class Config:
        orm_mode = True


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
