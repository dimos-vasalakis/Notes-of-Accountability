import uuid
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class PushSubscription(TimestampMixin, SQLModel, table=True):
    __tablename__ = "push_subscriptions"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True, ondelete="CASCADE")
    endpoint: str = Field(max_length=1024, unique=True, index=True)
    p256dh: str = Field(max_length=255)
    auth: str = Field(max_length=255)

    user: "User" = Relationship(back_populates="push_subscriptions")
