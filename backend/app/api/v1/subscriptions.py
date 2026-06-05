from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.api.deps import get_current_user
from backend.app.db.crud import create_subscription, get_user_subscriptions
from backend.app.db.session import get_session
from backend.app.schemas.subscription import SubscriptionCreate, SubscriptionRead

router = APIRouter(tags=["subscriptions"])


@router.post("/subscriptions", response_model=SubscriptionRead)
async def create_user_subscription(
    data: SubscriptionCreate,
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    subscription = await create_subscription(session, current_user.id, data)
    return subscription


@router.get("/subscriptions/me", response_model=list[SubscriptionRead])
async def list_current_user_subscriptions(
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    subscriptions = await get_user_subscriptions(session, current_user.id)
    return subscriptions
