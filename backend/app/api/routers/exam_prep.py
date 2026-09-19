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


@router.get("/config", response_model=ExamConfigRead)
async def get_config(
    current_user: User = Depends(require_student_mode),
    db: AsyncSession = Depends(get_db),
) -> ExamConfigRead:
    """Return the exam config and days-remaining countdown for the user's track."""
    return await exam_prep_service.get_exam_config(db, current_user.exam_track)


@router.get("/subjects", response_model=list[ExamSubjectRead])
async def list_subjects(
    current_user: User = Depends(require_student_mode),
    db: AsyncSession = Depends(get_db),
) -> list[ExamSubjectRead]:
    """List the exam subjects configured for the user's track."""
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
    """Log a completed focus/study session for the current user."""
    return await exam_prep_service.log_study_session(
        db, current_user.id, data, current_user.exam_track
    )


@router.get("/study-sessions", response_model=list[StudySessionRead])
async def list_study_sessions(
    window: Literal["week", "month"] = Query(default="week"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[StudySessionRead]:
    """List the user's study sessions within the requested time window."""
    return await exam_prep_service.list_study_sessions(db, current_user.id, window)


@router.get("/allocation", response_model=list[SubjectAllocationRead])
async def get_allocation(
    window: Literal["week", "month"] = Query(default="week"),
    current_user: User = Depends(require_student_mode),
    db: AsyncSession = Depends(get_db),
) -> list[SubjectAllocationRead]:
    """Return time spent per subject within the requested window."""
    return await exam_prep_service.get_subject_allocation(
        db, current_user.id, current_user.exam_track, window
    )
