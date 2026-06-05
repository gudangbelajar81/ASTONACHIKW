from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from backend.app.db.session import get_session
from backend.app.services.cycle_engine import calculate_cycle

router = APIRouter(tags=["cycle"])


class CyclePoint(BaseModel):
    date: str
    value: float


@router.get("/cycle", response_model=list[CyclePoint])
async def read_cycle(
    planet_a: str = Query(..., description="First planet (e.g., Sun, Moon, Venus, Mars, Jupiter, Saturn)"),
    planet_b: str = Query(..., description="Second planet (e.g., Sun, Moon, Venus, Mars, Jupiter, Saturn)"),
    start_date: date = Query(..., description="Start date in YYYY-MM-DD format"),
    end_date: date = Query(..., description="End date in YYYY-MM-DD format"),
    session: AsyncSession = Depends(get_session),
):
    try:
        cycles = await calculate_cycle(session, planet_a, planet_b, start_date, end_date)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not cycles:
        raise HTTPException(status_code=404, detail="No cycle data available for the given date range and planets.")

    return cycles
