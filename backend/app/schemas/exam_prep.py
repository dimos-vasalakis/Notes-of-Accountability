import uuid
from datetime import UTC, date, datetime, timedelta

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.exam_prep import StudySessionSource


class ExamSubjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name_el: str
    name_en: str
    weight_coefficient: float
    display_order: int


class ExamConfigRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    track: str
    academic_year: str
    exam_date: date
    days_remaining: int


# A session may be logged slightly ahead of the server clock, and may be
# backdated a little for one genuinely forgotten earlier session -- but no
# further. Streaks are the app's accountability currency, so a client must
# not be able to mint days it didn't earn.
_MAX_CLOCK_SKEW = timedelta(minutes=5)
_MAX_BACKDATE = timedelta(days=2)


class StudySessionCreate(BaseModel):
    subject_code: str | None = Field(default=None, max_length=64)
    duration_seconds: int = Field(gt=0, le=24 * 60 * 60)
    occurred_at: datetime | None = None
    source: StudySessionSource = StudySessionSource.FOCUS_TIMER

    @field_validator("occurred_at")
    @classmethod
    def validate_occurred_at(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return value
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        now = datetime.now(UTC)
        if value > now + _MAX_CLOCK_SKEW:
            # A future timestamp would also read as the user's most recent
            # activity forever, permanently suppressing inactivity nudges.
            raise ValueError("occurred_at cannot be in the future")
        if value < now - _MAX_BACKDATE:
            raise ValueError(
                f"occurred_at cannot be more than {_MAX_BACKDATE.days} days ago"
            )
        return value


class StudySessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    owner_id: uuid.UUID
    subject_code: str | None
    duration_seconds: int
    source: StudySessionSource
    occurred_at: datetime


class SubjectAllocationRead(BaseModel):
    """Planned (weight-derived) vs actual share of study time for one subject."""

    subject_code: str
    name_el: str
    name_en: str
    weight_coefficient: float
    planned_share: float
    actual_seconds: int
    actual_share: float
    delta: float
