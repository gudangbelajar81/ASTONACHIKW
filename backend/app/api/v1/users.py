from fastapi import APIRouter, Depends
from backend.app.api.deps import get_current_user
from backend.app.schemas.user import UserRead

router = APIRouter(tags=["users"])


@router.get("/users/me", response_model=UserRead)
async def read_current_user(current_user=Depends(get_current_user)):
    return current_user
