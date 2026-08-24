import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.user import User


class RefreshToken(SQLModel, table=True):
    __tablename__ = "refresh_tokens"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True, ondelete="CASCADE")
    token_hash: str = Field(max_length=255, unique=True, index=True)
    expires_at: datetime = Field(sa_type=DateTime(timezone=True))
    revoked: bool = Field(default=False)

    user: "User" = Relationship(back_populates="refresh_tokens")
