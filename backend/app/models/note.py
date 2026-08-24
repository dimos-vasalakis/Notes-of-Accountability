import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Text
from sqlmodel import Field, Relationship, SQLModel

from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class Note(TimestampMixin, SQLModel, table=True):
    __tablename__ = "notes"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    owner_id: uuid.UUID = Field(foreign_key="users.id", index=True, ondelete="CASCADE")
    title: str = Field(max_length=255)
    content: str = Field(default="", sa_type=Text, nullable=False)

    owner: "User" = Relationship(back_populates="notes")
