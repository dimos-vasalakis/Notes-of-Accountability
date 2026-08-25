import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PushSubscriptionKeys(BaseModel):
    p256dh: str
    auth: str


class PushSubscriptionCreate(BaseModel):
    endpoint: str
    keys: PushSubscriptionKeys


class PushSubscriptionDelete(BaseModel):
    endpoint: str


class PushSubscriptionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    endpoint: str
    created_at: datetime
