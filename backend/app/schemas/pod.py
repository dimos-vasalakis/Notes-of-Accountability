import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PodCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class PodJoin(BaseModel):
    invite_code: str = Field(min_length=1, max_length=12)


class PodRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    invite_code: str
    owner_id: uuid.UUID
    member_count: int
    created_at: datetime


class StreakRead(BaseModel):
    current_streak: int
    active_today: bool
    last_active_at: datetime | None


class PodMemberFeedItem(BaseModel):
    user_id: uuid.UUID
    display_name: str
    current_streak: int
    active_today: bool
    last_active_at: datetime | None


class PodFeedRead(BaseModel):
    pod: PodRead
    members: list[PodMemberFeedItem]
