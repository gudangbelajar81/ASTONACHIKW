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


class RegimeInfo(BaseModel):
    label: str
    trend_score: float
    volatility_score: float
    momentum_score: float
    risk_multiplier: float
    description: str


class PredictionResponse(BaseModel):
    ticker: str
    as_of_date: str
    horizon_days: int
    signal: str
    probability_up: float = Field(..., ge=0, le=1)
    confidence: str
    expected_return: float
    risk_label: str
    regime: RegimeInfo
    factors: list[PredictionFactor]
    backtest: BacktestMetrics


class PredictionSnapshotRead(BaseModel):
    as_of_date: str
    horizon_days: int
    signal: str
    probability_up: float
    confidence: str
    expected_return: float | None
    realized_return: float | None


class ModelWeightResponse(BaseModel):
    ticker: str
    horizon_days: int
    weights: dict[str, float]
    sample_count: int
    hit_rate: float
    average_signal_return: float
    method: str
    trained_at: str | None = None


class PerformanceResponse(BaseModel):
    ticker: str
    horizon_days: int
    backtest: BacktestMetrics
    latest_prediction: PredictionResponse
    model_weights: ModelWeightResponse
    snapshots: list[PredictionSnapshotRead]
    verdict: str
