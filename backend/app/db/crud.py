from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.security import get_password_hash, verify_password
from backend.app.db.models import Subscription, User, UserAppState
from backend.app.schemas.subscription import SubscriptionCreate
from backend.app.schemas.user import UserCreate


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    query = select(User).where(User.email == email.lower())
    result = await session.execute(query)
    return result.scalars().first()


async def get_user(session: AsyncSession, user_id: int) -> User | None:
    query = select(User).where(User.id == user_id)
    result = await session.execute(query)
    return result.scalars().first()


async def create_user(session: AsyncSession, user_create: UserCreate) -> User:
    hashed_password = get_password_hash(user_create.password)
    user = User(email=user_create.email.lower(), hashed_password=hashed_password)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def authenticate_user(session: AsyncSession, email: str, password: str) -> User | None:
    user = await get_user_by_email(session, email)
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user


async def create_subscription(session: AsyncSession, user_id: int, subscription_in: SubscriptionCreate) -> Subscription:
    subscription = Subscription(
        user_id=user_id,
        plan=subscription_in.plan,
        status=subscription_in.status,
        started_at=datetime.utcnow(),
        expires_at=subscription_in.expires_at,
    )
    session.add(subscription)
    await session.commit()
    await session.refresh(subscription)
    return subscription


async def get_user_subscriptions(session: AsyncSession, user_id: int) -> list[Subscription]:
    query = select(Subscription).where(Subscription.user_id == user_id).order_by(Subscription.started_at.desc())
    result = await session.execute(query)
    return result.scalars().all()


async def get_user_app_state(session: AsyncSession, user_id: int) -> UserAppState | None:
    query = select(UserAppState).where(UserAppState.user_id == user_id)
    result = await session.execute(query)
    return result.scalars().first()


async def upsert_user_app_state(session: AsyncSession, user_id: int, payload: dict) -> UserAppState:
    state = await get_user_app_state(session, user_id)
    if state:
        state.payload = payload
    else:
        state = UserAppState(user_id=user_id, payload=payload)
        session.add(state)
    await session.commit()
    await session.refresh(state)
    return state
