from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.deps import get_current_user
from backend.app.db.crud import get_user_app_state, upsert_user_app_state
from backend.app.db.session import get_session
from backend.app.schemas.app_state import AppStatePayload, AppStateRead

router = APIRouter(tags=["app-state"])


@router.get("/app-state/me", response_model=AppStateRead | None)
async def read_my_app_state(
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await get_user_app_state(session, current_user.id)


@router.put("/app-state/me", response_model=AppStateRead)
async def save_my_app_state(
    data: AppStatePayload,
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await upsert_user_app_state(session, current_user.id, data.payload)
