from fastapi import APIRouter
from backend.app.api.v1 import auth, subscriptions, users
from backend.app.api.v1 import endpoints

router = APIRouter()
router.include_router(endpoints.router)
router.include_router(auth.router)
router.include_router(users.router)
router.include_router(subscriptions.router)
