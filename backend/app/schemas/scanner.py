from pydantic import BaseModel


class ScannerResult(BaseModel):
    cycle: str
    correlation: float
    lag_days: int
    accuracy: float
    score: float
    sample_count: int


class ScannerResponse(BaseModel):
    ticker: str
    lookback_years: int
    combinations_tested: int
    top_combinations: list[ScannerResult]
