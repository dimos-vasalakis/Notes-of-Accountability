import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Text
from sqlalchemy import Enum as SAEnum
from sqlmodel import Field, Relationship, SQLModel

from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class TaskStatus(str, enum.Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"


class Task(TimestampMixin, SQLModel, table=True):
    __tablename__ = "tasks"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    owner_id: uuid.UUID = Field(foreign_key="users.id", index=True, ondelete="CASCADE")
    title: str = Field(max_length=255)
    description: str | None = Field(default=None, sa_type=Text)
    status: TaskStatus = Field(
        default=TaskStatus.TODO,
        sa_type=SAEnum(TaskStatus, native_enum=False, length=20),
    )
    due_date: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))
    notified_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))

    owner: "User" = Relationship(back_populates="tasks")
