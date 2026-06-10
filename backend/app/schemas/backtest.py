from datetime import date
from pydantic import BaseModel, Field
from typing import Any


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
    setup_type: str | None = None


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


# ── Setup Backtest (NEW) ──────────────────────────────────────────

class SetupBacktestRequest(BaseModel):
    ticker: str
    start_date: date
    end_date: date
    horizon: str = Field(default="5d", description="1d, 5d, or 20d")
    stop_loss: float = Field(default=0.03, description="Percent as 0.03 or 3")
    target_profit: float = Field(default=0.06, description="Percent as 0.06 or 6")


class SetupPerformance(BaseModel):
    setup_type: str
    total_trades: int
    win_rate: float | None = None
    average_return: float | None = None
    max_drawdown: float | None = None
    profit_factor: float | None = None
    expectancy: float | None = None
    avg_score: int | None = None
    verdict: str
    best_trade: dict | None = None
    worst_trade: dict | None = None


class SetupBacktestResponse(BaseModel):
    ticker: str
    start_date: str
    end_date: str
    horizon: str
    stop_loss: float
    target_profit: float
    setup_performance: dict[str, SetupPerformance]
    ranked_setups: list[str]
    best_setup: str | None = None
    best_setup_note: str


# ── Screener ─────────────────────────────────────────────────────

class LiquidityWarningItem(BaseModel):
    code: str
    severity: str
    message: str


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
    calibrated_probability: float | None = None
    horizon: str
    last_price: float
    entry_zone: list[float]
    target_1: float
    target_2: float
    target_3: float | None = None
    stop_loss: float
    risk_reward: float
    avg_volume_20d: float
    avg_value_20d: float
    volume_ratio_5d: float
    relative_strength: float
    bandarmology: str
    setup_type: str | None = None
    market_structure: str | None = None
    trend_state: str | None = None
    backtest_confidence: str | None = None
    backtest_win_rate: float | None = None
    backtest_profit_factor: float | None = None
    reasons: list[str]
    risks: list[str]
    # ── Liquidity & Gorengan WARNING fields ────────────────
    liquidity_grade: str | None = None
    is_gorengan: bool | None = None
    gorengan_risk_level: str | None = None
    liquidity_summary: str | None = None
    liquidity_recommendation: str | None = None
    liquidity_warnings: list[LiquidityWarningItem] | None = None


class ScreenerResponse(BaseModel):
    horizon: str
    universe_size: int
    scanned_size: int
    top_daily: list[ScreenerItem]
    top_weekly: list[ScreenerItem]
    top_monthly: list[ScreenerItem]
    avoid_high_risk: list[ScreenerItem]
    # ── NEW: Gorengan Watchlist ────────────────────────────
    gorengan_watchlist: list[ScreenerItem] | None = None
    gorengan_watchlist_note: str | None = None
