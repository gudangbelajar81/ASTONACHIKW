from datetime import date
from pydantic import BaseModel, Field


class PredictionScoreRequest(BaseModel):
    ticker: str
    horizon: str = "weekly"
    market: str = "id"
    backtest_start: date | None = None
    backtest_end: date | None = None


class ScoreMetric(BaseModel):
    value: int
    max: int
    explanation: str


class BacktestConfidence(BaseModel):
    available: bool
    win_rate: float | None = None
    average_return: float | None = None
    max_drawdown: float | None = None
    profit_factor: float | None = None
    expectancy: float | None = None
    total_trade: int = 0
    beats_ihsg: bool | None = None
    verdict: str


class PredictionScoreResponse(BaseModel):
    symbol: str
    market: str
    horizon: str
    final_score: int
    signal: str
    confidence: float
    last_price: float
    entry_zone: list[float]
    target_1: float
    target_2: float
    stop_loss: float
    risk_reward: float
    score_components: dict[str, ScoreMetric]
    main_reasons: list[str]
    main_risks: list[str]
    invalidation: str
    scenario: str
    backtest_confidence: BacktestConfidence
    data_quality: dict
