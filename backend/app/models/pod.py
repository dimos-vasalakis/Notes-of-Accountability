import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, UniqueConstraint, func
from sqlmodel import Field, Relationship, SQLModel

from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class Pod(TimestampMixin, SQLModel, table=True):
    """A small accountability group joined via an invite code."""

    __tablename__ = "pods"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(max_length=100)
    invite_code: str = Field(max_length=12, unique=True, index=True)
    owner_id: uuid.UUID = Field(foreign_key="users.id", index=True, ondelete="CASCADE")

    memberships: list["PodMembership"] = Relationship(
        back_populates="pod", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )


class PodMembership(SQLModel, table=True):
    __tablename__ = "pod_memberships"
    __table_args__ = (UniqueConstraint("pod_id", "user_id", name="uq_pod_membership"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    pod_id: uuid.UUID = Field(foreign_key="pods.id", index=True, ondelete="CASCADE")
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True, ondelete="CASCADE")
    joined_at: datetime = Field(
        sa_type=DateTime(timezone=True),
        nullable=False,
        sa_column_kwargs={"server_default": func.now()},
    )
    # Debounces the inactivity nudge so a member who stays quiet for days
    # doesn't spam their pod on every scheduler tick.
    last_nudge_sent_at: datetime | None = Field(
        default=None, sa_type=DateTime(timezone=True)
    )

    pod: "Pod" = Relationship(back_populates="memberships")
    user: "User" = Relationship(back_populates="pod_memberships")
