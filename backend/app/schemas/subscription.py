from datetime import datetime
from pydantic import BaseModel, ConfigDict


class SubscriptionCreate(BaseModel):
    plan: str
    status: str
    expires_at: datetime


class SubscriptionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    plan: str
    status: str
    started_at: datetime
    expires_at: datetime
