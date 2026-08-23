import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class NoteCreate(BaseModel):
    title: str
    content: str = ""


class NoteUpdate(BaseModel):
    title: str | None = None
    content: str | None = None


class NoteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    owner_id: uuid.UUID
    title: str
    content: str
    created_at: datetime
    updated_at: datetime
