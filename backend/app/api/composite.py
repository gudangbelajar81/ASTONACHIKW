from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.session import get_session
from backend.app.schemas.composite import CompositeRequestBody, CompositeResponse
from backend.app.services.composite_engine import (
    CycleCombination,
    calculate_composite_cycle,
    apply_smoothing,
    project_future_values,
)

router = APIRouter(tags=["composite"])


@router.post("/composite", response_model=list[CompositeResponse])
async def read_composite(
    request: CompositeRequestBody,
    session: AsyncSession = Depends(get_session),
):
    try:
        start_date = datetime.strptime(request.start_date, "%Y-%m-%d").date()
        end_date = datetime.strptime(request.end_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

    combinations = []
    for combo_input in request.combinations:
        try:
            combinations.append(
                CycleCombination(combo_input.planet_a, combo_input.planet_b, combo_input.weight)
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    try:
        composite_data = await calculate_composite_cycle(session, combinations, start_date, end_date)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not composite_data:
        raise HTTPException(status_code=404, detail="No composite cycle data available for the given date range.")

    smoothed_7d_map = {}
    smoothed_30d_map = {}
    smoothed_60d_map = {}

    if 7 in request.smoothing_windows:
        smoothed_7d = apply_smoothing(composite_data, 7)
        smoothed_7d_map = {item["date"]: item["smoothed"] for item in smoothed_7d}

    if 30 in request.smoothing_windows:
        smoothed_30d = apply_smoothing(composite_data, 30)
        smoothed_30d_map = {item["date"]: item["smoothed"] for item in smoothed_30d}

    if 60 in request.smoothing_windows:
        smoothed_60d = apply_smoothing(composite_data, 60)
        smoothed_60d_map = {item["date"]: item["smoothed"] for item in smoothed_60d}

    response_data = []
    for point in composite_data:
        response_data.append(
            CompositeResponse(
                date=point["date"],
                value=point["value"],
                smoothed_7d=smoothed_7d_map.get(point["date"]),
                smoothed_30d=smoothed_30d_map.get(point["date"]),
                smoothed_60d=smoothed_60d_map.get(point["date"]),
                projected=False,
            )
        )

    if request.project_days > 0:
        projections = project_future_values(composite_data, request.project_days)
        for proj in projections:
            response_data.append(
                CompositeResponse(
                    date=proj["date"],
                    value=proj["value"],
                    smoothed_7d=None,
                    smoothed_30d=None,
                    smoothed_60d=None,
                    projected=True,
                )
            )

    return response_data
