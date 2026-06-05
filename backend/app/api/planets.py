from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.session import get_session
from backend.app.schemas.planet import PlanetPositions
from backend.app.services.ephemeris_service import get_planetary_positions

router = APIRouter(tags=["planets"])


@router.get("/planets", response_model=PlanetPositions)
async def read_planets(
    date: date | None = Query(None, description="Optional target date in YYYY-MM-DD format."),
    session: AsyncSession = Depends(get_session),
):
    positions = await get_planetary_positions(session, date)
    if positions is None:
        raise HTTPException(status_code=404, detail="No planetary positions available for this date.")
    return positions
