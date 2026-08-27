from datetime import UTC, datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_student_mode
from app.core.db import get_db
from app.models.exam_prep import StudySession
from app.models.user import User
from app.schemas.exam_prep import (
    ExamConfigRead,
    ExamSubjectRead,
    StudySessionCreate,
    StudySessionRead,
    SubjectAllocationRead,
)
from app.services import exam_prep_service

router = APIRouter(prefix="/api/exam-prep", tags=["exam-prep"])

_WINDOW_DAYS = {"week": 7, "month": 30}


def _window_start(window: str) -> datetime:
    return datetime.now(UTC) - timedelta(days=_WINDOW_DAYS[window])


@router.get("/config", response_model=ExamConfigRead)
async def get_config(
    current_user: User = Depends(require_student_mode),
    db: AsyncSession = Depends(get_db),
) -> ExamConfigRead:
    config = await exam_prep_service.get_exam_config(db, current_user.exam_track)
    return ExamConfigRead(
        track=config.track,
        academic_year=config.academic_year,
        exam_date=config.exam_date,
        days_remaining=exam_prep_service.days_remaining(config),
    )


@router.get("/subjects", response_model=list[ExamSubjectRead])
async def list_subjects(
    current_user: User = Depends(require_student_mode),
    db: AsyncSession = Depends(get_db),
) -> list[ExamSubjectRead]:
    return await exam_prep_service.list_subjects(db, current_user.exam_track)


@router.post(
    "/study-sessions",
    response_model=StudySessionRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_study_session(
    data: StudySessionCreate,
    # Deliberately not student-gated: a focus session counts toward everyone's
    # streak, and the app tells every user so. Only subject tagging needs a track.
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StudySession:
    return await exam_prep_service.log_study_session(
        db, current_user.id, data, current_user.exam_track
    )


@router.get("/study-sessions", response_model=list[StudySessionRead])
async def list_study_sessions(
    window: Literal["week", "month"] = Query(default="week"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[StudySession]:
    return await exam_prep_service.list_study_sessions(
        db, current_user.id, _window_start(window)
    )


@router.get("/allocation", response_model=list[SubjectAllocationRead])
async def get_allocation(
    window: Literal["week", "month"] = Query(default="week"),
    current_user: User = Depends(require_student_mode),
    db: AsyncSession = Depends(get_db),
) -> list[SubjectAllocationRead]:
    return await exam_prep_service.get_subject_allocation(
        db, current_user.id, current_user.exam_track, _window_start(window)
    )
