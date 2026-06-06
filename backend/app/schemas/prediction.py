from pydantic import BaseModel, Field
from backend.app.schemas.context import MacroContextResponse, SentimentResponse


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


class ScenarioPlan(BaseModel):
    entry_zone_low: float
    entry_zone_high: float
    invalidation_level: float
    bullish_target: float
    bearish_target: float
    position_size_shares: int
    risk_amount: float
    risk_per_share: float
    playbook: str


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
    sentiment: SentimentResponse | None = None
    macro: MacroContextResponse | None = None
    scenario: ScenarioPlan | None = None
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


class WatchlistItem(BaseModel):
    ticker: str
    signal: str
    probability_up: float
    confidence: str
    expected_return: float
    risk_label: str
    regime: str
    sentiment: str
    risk_budget: str


class WatchlistResponse(BaseModel):
    horizon_days: int
    items: list[WatchlistItem]
