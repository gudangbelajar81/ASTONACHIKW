from pydantic import BaseModel, Field


class PredictionFactor(BaseModel):
    name: str
    value: float
    weight: float
    contribution: float
    description: str


class BacktestMetrics(BaseModel):
    sample_count: int
    hit_rate: float
    average_forward_return: float
    average_signal_return: float
    max_drawdown: float


class PredictionResponse(BaseModel):
    ticker: str
    as_of_date: str
    horizon_days: int
    signal: str
    probability_up: float = Field(..., ge=0, le=1)
    confidence: str
    expected_return: float
    risk_label: str
    factors: list[PredictionFactor]
    backtest: BacktestMetrics
