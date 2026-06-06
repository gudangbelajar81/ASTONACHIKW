from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional


class CompositeCyclePoint(BaseModel):
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    value: float = Field(..., description="Cycle value between -1 and 1")


class TurningPointData(BaseModel):
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    type: str = Field(..., description="TOP or BOTTOM")
    strength: int = Field(..., ge=0, le=100, description="Strength 0-100")


class ScannerResultData(BaseModel):
    cycle: str = Field(..., description="Planet combination (e.g., Venus-Jupiter)")
    correlation: float = Field(..., description="Correlation value")
    lag_days: int = Field(..., description="Lag in days")
    accuracy: float = Field(..., description="Accuracy 0-1")
    score: float = Field(..., description="Overall score")


class AnalystRequestBody(BaseModel):
    ticker: str = Field(..., description="Market ticker (e.g., AAPL, ^JKSE)")
    composite_cycle_data: List[CompositeCyclePoint] = Field(
        ..., description="Recent composite cycle data"
    )
    turning_points: List[TurningPointData] = Field(
        ..., description="Detected turning points"
    )
    scanner_results: Optional[List[ScannerResultData]] = Field(
        default=None, description="Top scanner results"
    )
    ai_provider_order: Optional[List[str]] = Field(
        default=None, description="Preferred AI provider order"
    )
    ai_api_keys: Optional[Dict[str, List[str]]] = Field(
        default=None, description="User-provided API keys by provider"
    )
    ai_models: Optional[Dict[str, str]] = Field(
        default=None, description="User-selected AI model by provider"
    )


class AnalystKeyTestRequest(BaseModel):
    provider: str = Field(..., description="AI provider name")
    api_key: str = Field(..., description="API key to test")
    model: Optional[str] = Field(default=None, description="Model override")


class AnalystKeyTestResponse(BaseModel):
    provider: str
    status: str
    detail: str


class AnalystResponse(BaseModel):
    ticker: str = Field(..., description="Market ticker")
    summary: str = Field(..., description="1-2 sentence overview")
    cycle_explanation: str = Field(..., description="Explanation of composite cycle trend")
    turning_points_explanation: str = Field(..., description="Analysis of recent turning points")
    scan_explanation: str = Field(..., description="Insights from scanner results")
    outlook: str = Field(..., description="Forward-looking market perspective")
