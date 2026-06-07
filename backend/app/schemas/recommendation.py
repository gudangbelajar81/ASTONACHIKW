from pydantic import BaseModel

from backend.app.schemas.bandarmology import MarketDataProviderInput


class RecommendationRequest(BaseModel):
    ticker: str
    horizon: str = "weekly"
    market: str = "id"
    market_data_providers: list[MarketDataProviderInput] = []


class RecommendationDataQuality(BaseModel):
    ohlcv_available: bool
    bandarmology_available: bool
    macro_available: bool
    fundamental_available: bool


class RecommendationPriceContext(BaseModel):
    last_price: float
    ma20: float | None = None
    ma50: float | None = None
    ma200: float | None = None
    support: float
    resistance: float
    volume_ratio_5d: float
    relative_strength: float


class RecommendationValidation(BaseModel):
    backtest_win_rate: float | None = None
    sample_size: int
    max_drawdown: float | None = None
    last_updated: str


class RecommendationResponse(BaseModel):
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
    score_breakdown: dict[str, int]
    main_reasons: list[str]
    main_risks: list[str]
    price_context: RecommendationPriceContext
    data_quality: RecommendationDataQuality
    validation: RecommendationValidation
