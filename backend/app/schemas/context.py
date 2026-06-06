from pydantic import BaseModel


class NewsSentimentItem(BaseModel):
    title: str
    publisher: str
    url: str
    score: float


class SentimentResponse(BaseModel):
    ticker: str
    label: str
    score: float
    headline_count: int
    description: str
    items: list[NewsSentimentItem]


class MacroContextResponse(BaseModel):
    benchmark: str
    beta: float
    correlation: float
    relative_strength: float
    market_regime: str
    risk_budget: str
    description: str
