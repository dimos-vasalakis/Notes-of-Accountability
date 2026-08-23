import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.task import TaskStatus


class TaskCreate(BaseModel):
    title: str
    description: str | None = None
    due_date: datetime | None = None


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: TaskStatus | None = None
    due_date: datetime | None = None


class TaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    owner_id: uuid.UUID
    title: str
    description: str | None
    status: TaskStatus
    due_date: datetime | None
    created_at: datetime
    updated_at: datetime
