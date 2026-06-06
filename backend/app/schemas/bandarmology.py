from pydantic import BaseModel


class OHLCVPoint(BaseModel):
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    ma20: float | None = None
    ma50: float | None = None
    ma200: float | None = None


class BandarmologyResponse(BaseModel):
    ticker: str
    as_of_date: str
    smart_money_score: float
    accumulation_score: float
    distribution_score: float
    volume_spike: float
    obv_trend: str
    money_flow_score: float
    support: float
    resistance: float
    verdict: str
    notes: list[str]


class OHLCVResponse(BaseModel):
    ticker: str
    points: list[OHLCVPoint]
    bandarmology: BandarmologyResponse
