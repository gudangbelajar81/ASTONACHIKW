from datetime import date
from pydantic import BaseModel, Field


class BacktestRequest(BaseModel):
    ticker: str
    start_date: date
    end_date: date
    horizon: str = Field(default="5d", description="1d, 5d, or 20d")
    rule_entry: str = "score_gt_70"
    rule_exit: str = "target_stop_or_horizon"
    stop_loss: float = Field(default=0.03, description="Percent as 0.03 or 3")
    target_profit: float = Field(default=0.06, description="Percent as 0.06 or 6")


class TradeResult(BaseModel):
    entry_date: str
    exit_date: str
    entry_price: float
    exit_price: float
    return_pct: float
    score: int
    exit_reason: str


class BacktestThresholdCheck(BaseModel):
    threshold: int
    trade_count: int
    win_rate: float | None = None
    average_forward_return: float | None = None
    random_average_return: float | None = None
    better_than_random: bool | None = None


class BacktestResponse(BaseModel):
    ticker: str
    start_date: str
    end_date: str
    horizon: str
    rule_entry: str
    rule_exit: str
    total_trade: int
    win_rate: float | None = None
    average_return: float | None = None
    max_drawdown: float | None = None
    expectancy: float | None = None
    profit_factor: float | None = None
    best_trade: TradeResult | None = None
    worst_trade: TradeResult | None = None
    threshold_checks: list[BacktestThresholdCheck]
    benchmark: dict
    trades: list[TradeResult]


class ScreenerRequest(BaseModel):
    horizon: str = "daily"
    min_volume: int = 1_000_000
    min_value: float = 5_000_000_000
    top_n: int = Field(default=20, ge=1, le=50)
    tickers: list[str] | None = None


class ScreenerItem(BaseModel):
    symbol: str
    final_score: int
    signal: str
    horizon: str
    last_price: float
    entry_zone: list[float]
    target_1: float
    target_2: float
    stop_loss: float
    risk_reward: float
    avg_volume_20d: float
    avg_value_20d: float
    volume_ratio_5d: float
    relative_strength: float
    bandarmology: str
    backtest_confidence: str | None = None
    backtest_win_rate: float | None = None
    backtest_profit_factor: float | None = None
    reasons: list[str]
    risks: list[str]


class ScreenerResponse(BaseModel):
    horizon: str
    universe_size: int
    scanned_size: int
    top_daily: list[ScreenerItem]
    top_weekly: list[ScreenerItem]
    top_monthly: list[ScreenerItem]
    avoid_high_risk: list[ScreenerItem]
