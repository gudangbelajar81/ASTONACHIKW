from datetime import datetime
from pydantic import BaseModel


class SubscriptionCreate(BaseModel):
    plan: str
    status: str
    expires_at: datetime


class SubscriptionRead(BaseModel):
    id: int
    plan: str
    status: str
    started_at: datetime
    expires_at: datetime

    class Config:
        orm_mode = True
