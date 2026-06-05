from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.security import OAuth2PasswordRequestForm
from backend.app.core.security import create_access_token
from backend.app.db.crud import authenticate_user, create_user, get_user_by_email
from backend.app.db.session import get_session
from backend.app.schemas.token import Token
from backend.app.schemas.user import UserCreate, UserRead

router = APIRouter(tags=["auth"])


@router.post("/auth/signup", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def signup(user_in: UserCreate, session: AsyncSession = Depends(get_session)):
    existing = await get_user_by_email(session, user_in.email)
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User already exists")
    user = await create_user(session, user_in)
    return user


@router.post("/auth/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), session: AsyncSession = Depends(get_session)):
    user = await authenticate_user(session, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")
    access_token = create_access_token(subject=str(user.id), expires_delta=timedelta(minutes=60))
    return Token(access_token=access_token, token_type="bearer")
