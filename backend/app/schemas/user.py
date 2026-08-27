import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.exam_prep import SUPPORTED_EXAM_TRACKS


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    is_student: bool = False
    display_name: str | None = Field(default=None, max_length=64)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class UserLogin(BaseModel):
    email: EmailStr
    password: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class UserProfileUpdate(BaseModel):
    is_student: bool | None = None
    exam_track: str | None = Field(default=None, max_length=32)
    display_name: str | None = Field(default=None, max_length=64)

    @field_validator("is_student")
    @classmethod
    def reject_null_is_student(cls, value: bool | None) -> bool | None:
        # None here means "omitted" (the default, which is not validated).
        # An explicit null would otherwise be written to a NOT NULL column.
        if value is None:
            raise ValueError("is_student cannot be null; omit it to leave unchanged")
        return value

    @field_validator("exam_track")
    @classmethod
    def validate_exam_track(cls, value: str | None) -> str | None:
        # Rejecting unknown values keeps an account from being wedged into a
        # track that has no subjects, where every exam-prep call 404s and the
        # opt-in screen is skipped because is_student is already true.
        if value is not None and value not in SUPPORTED_EXAM_TRACKS:
            raise ValueError(
                f"Unsupported exam track. Expected one of: "
                f"{', '.join(sorted(SUPPORTED_EXAM_TRACKS))}"
            )
        return value


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    created_at: datetime
    is_student: bool
    exam_track: str | None
    display_name: str | None
