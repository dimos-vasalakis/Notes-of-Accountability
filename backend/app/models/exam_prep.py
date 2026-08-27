import enum
import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime
from sqlalchemy import Enum as SAEnum
from sqlmodel import Field, Relationship, SQLModel

from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


# Orientation tracks with seeded subjects. Extend alongside a seed migration
# (and the (track, code) uniqueness this implies) when adding a track.
DEFAULT_EXAM_TRACK = "group_d"
SUPPORTED_EXAM_TRACKS = frozenset({DEFAULT_EXAM_TRACK})


class ExamSubject(SQLModel, table=True):
    """A Panhellenic-examined subject and its weight toward the final score.

    Rows are seeded data, not constants: coefficients change year to year, so
    they live in the DB and are re-edited via scripts/seed_exam_config.py.
    """

    __tablename__ = "exam_subjects"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    track: str = Field(max_length=32, index=True)
    code: str = Field(max_length=64, unique=True, index=True)
    name_el: str = Field(max_length=128)
    name_en: str = Field(max_length=128)
    weight_coefficient: float
    display_order: int = Field(default=0)
    is_active: bool = Field(default=True)


class ExamConfig(SQLModel, table=True):
    """Per-track exam-season settings. One active row per track."""

    __tablename__ = "exam_configs"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    track: str = Field(max_length=32, unique=True, index=True)
    academic_year: str = Field(max_length=16)
    exam_date: date = Field(sa_type=Date)
    is_active: bool = Field(default=True)


class StudySessionSource(str, enum.Enum):
    FOCUS_TIMER = "focus_timer"
    MANUAL = "manual"


class StudySession(TimestampMixin, SQLModel, table=True):
    """A completed block of study time, optionally tagged with a subject.

    This is the server-side activity trail that makes cross-user streaks
    possible — the focus timer's own stats are client-side only.
    """

    __tablename__ = "study_sessions"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    owner_id: uuid.UUID = Field(foreign_key="users.id", index=True, ondelete="CASCADE")
    # Soft reference to ExamSubject.code, deliberately not a FK: subjects are
    # reseeded each exam season and that must not orphan historical sessions.
    subject_code: str | None = Field(default=None, max_length=64, index=True)
    duration_seconds: int
    source: StudySessionSource = Field(
        default=StudySessionSource.FOCUS_TIMER,
        sa_type=SAEnum(StudySessionSource, native_enum=False, length=20),
    )
    occurred_at: datetime = Field(sa_type=DateTime(timezone=True), index=True)

    owner: "User" = Relationship(back_populates="study_sessions")
