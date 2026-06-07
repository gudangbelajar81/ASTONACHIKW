from pydantic import BaseModel
from backend.app.schemas.prediction import PredictionResponse


class WorkflowTimeframeSummary(BaseModel):
    label: str
    horizon_days: int
    signal: str
    probability_up: float
    confidence: str
    expected_return: float
    risk_label: str
    summary: str


class WorkflowItem(BaseModel):
    ticker: str
    rank_score: float
    recommended_action: str
    entry_zone_low: float
    entry_zone_high: float
    target_price: float
    stop_loss: float
    reasons: list[str]
    daily: WorkflowTimeframeSummary
    weekly: WorkflowTimeframeSummary
    monthly: WorkflowTimeframeSummary
    latest_prediction: PredictionResponse


class WorkflowResponse(BaseModel):
    market: str
    universe_size: int
    scanned_size: int
    items: list[WorkflowItem]
