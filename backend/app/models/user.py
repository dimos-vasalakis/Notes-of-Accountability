import uuid
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.exam_prep import StudySession
    from app.models.note import Note
    from app.models.pod import PodMembership
    from app.models.push_subscription import PushSubscription
    from app.models.refresh_token import RefreshToken
    from app.models.task import Task


class User(TimestampMixin, SQLModel, table=True):
    __tablename__ = "users"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    email: str = Field(max_length=255, unique=True, index=True)
    hashed_password: str = Field(max_length=255)
    is_active: bool = Field(default=True)
    is_student: bool = Field(default=False)
    exam_track: str | None = Field(default=None, max_length=32)
    # Shown to pod-mates instead of the email address.
    display_name: str | None = Field(default=None, max_length=64)

    notes: list["Note"] = Relationship(
        back_populates="owner", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    tasks: list["Task"] = Relationship(
        back_populates="owner", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    refresh_tokens: list["RefreshToken"] = Relationship(
        back_populates="user", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    push_subscriptions: list["PushSubscription"] = Relationship(
        back_populates="user", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    study_sessions: list["StudySession"] = Relationship(
        back_populates="owner", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    pod_memberships: list["PodMembership"] = Relationship(
        back_populates="user", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
