from fastapi import APIRouter, HTTPException
from backend.app.schemas.analyst import (
    AnalystKeyTestRequest,
    AnalystKeyTestResponse,
    AnalystRequestBody,
    AnalystResponse,
)
from backend.app.services.ai_analyst import AnalystInput, analyze_market, test_provider_key

router = APIRouter()


@router.post("/analyst", response_model=AnalystResponse)
async def get_market_analysis(request: AnalystRequestBody) -> AnalystResponse:
    """
    Generate AI-powered market analysis based on composite cycles, turning points, and scanner results.

    Request body:
    - ticker: Market ticker (required)
    - composite_cycle_data: List of recent cycle points (required)
    - turning_points: List of detected turning points (required)
    - scanner_results: Top planetary combinations (optional)

    Returns:
    - summary: Brief cycle state overview
    - cycle_explanation: Trend interpretation
    - turning_points_explanation: Top/bottom analysis
    - scan_explanation: Strongest combinations insight
    - outlook: Forward-looking perspective
    """
    try:
        # Convert request data to AnalystInput
        analyst_input = AnalystInput(
            ticker=request.ticker,
            composite_cycle_data=[d.dict() for d in request.composite_cycle_data],
            turning_points=[d.dict() for d in request.turning_points],
            scanner_results=[d.dict() for d in request.scanner_results] if request.scanner_results else [],
            ai_provider_order=request.ai_provider_order,
            ai_api_keys=request.ai_api_keys,
            ai_models=request.ai_models,
        )

        # Generate analysis
        analysis = await analyze_market(analyst_input)

        return AnalystResponse(
            ticker=analysis.ticker,
            summary=analysis.summary,
            cycle_explanation=analysis.cycle_explanation,
            turning_points_explanation=analysis.turning_points_explanation,
            scan_explanation=analysis.scan_explanation,
            outlook=analysis.outlook,
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating analysis: {str(e)}")


@router.post("/analyst/test-key", response_model=AnalystKeyTestResponse)
async def test_ai_key(request: AnalystKeyTestRequest) -> AnalystKeyTestResponse:
    try:
        test_provider_key(request.provider, request.api_key, request.model)
        return AnalystKeyTestResponse(
            provider=request.provider,
            status="live",
            detail="Key aktif dan bisa dipakai.",
        )
    except Exception as exc:
        return AnalystKeyTestResponse(
            provider=request.provider,
            status="dead",
            detail=str(exc),
        )
