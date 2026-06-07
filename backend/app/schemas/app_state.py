from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict


class AppStatePayload(BaseModel):
    payload: dict[str, Any]


class AppStateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    payload: dict[str, Any]
    created_at: datetime
    updated_at: datetime
