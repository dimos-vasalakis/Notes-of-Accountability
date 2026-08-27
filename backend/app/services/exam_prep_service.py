import uuid
from datetime import UTC, date, datetime

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.exceptions import NotFoundError
from app.models.exam_prep import ExamConfig, ExamSubject, StudySession
from app.schemas.exam_prep import StudySessionCreate, SubjectAllocationRead


async def get_exam_config(db: AsyncSession, track: str) -> ExamConfig:
    config = await db.scalar(
        select(ExamConfig).where(
            ExamConfig.track == track, ExamConfig.is_active.is_(True)
        )
    )
    if config is None:
        raise NotFoundError(f"No exam configuration found for track '{track}'")
    return config


def days_remaining(config: ExamConfig, as_of: date | None = None) -> int:
    """Days until the first exam. Negative once the exams have passed."""
    return (config.exam_date - (as_of or datetime.now(UTC).date())).days


async def list_subjects(db: AsyncSession, track: str) -> list[ExamSubject]:
    result = await db.scalars(
        select(ExamSubject)
        .where(ExamSubject.track == track, ExamSubject.is_active.is_(True))
        .order_by(ExamSubject.display_order)
    )
    return list(result)


async def log_study_session(
    db: AsyncSession, owner_id: uuid.UUID, data: StudySessionCreate, track: str | None
) -> StudySession:
    """Record study time. Untagged sessions are allowed for any user; a tagged
    one must name a subject in the caller's own track, otherwise the time would
    be accepted and then silently dropped from their allocation report.
    """
    if data.subject_code is not None:
        if track is None:
            raise NotFoundError(
                "Cannot tag a subject without an exam track; enable student mode first"
            )
        known = await db.scalar(
            select(ExamSubject.code).where(
                ExamSubject.code == data.subject_code,
                ExamSubject.track == track,
                ExamSubject.is_active.is_(True),
            )
        )
        if known is None:
            raise NotFoundError(f"Unknown subject '{data.subject_code}'")

    session = StudySession(
        owner_id=owner_id,
        subject_code=data.subject_code,
        duration_seconds=data.duration_seconds,
        source=data.source,
        occurred_at=data.occurred_at or datetime.now(UTC),
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


async def list_study_sessions(
    db: AsyncSession, owner_id: uuid.UUID, since: datetime
) -> list[StudySession]:
    result = await db.scalars(
        select(StudySession)
        .where(StudySession.owner_id == owner_id, StudySession.occurred_at >= since)
        .order_by(StudySession.occurred_at.desc())
    )
    return list(result)


async def get_subject_allocation(
    db: AsyncSession, owner_id: uuid.UUID, track: str, since: datetime
) -> list[SubjectAllocationRead]:
    """Compare each subject's weight-derived target share against time actually spent."""
    subjects = await list_subjects(db, track)
    if not subjects:
        return []

    totals = dict(
        (
            await db.execute(
                select(
                    StudySession.subject_code,
                    func.sum(StudySession.duration_seconds),
                )
                .where(
                    StudySession.owner_id == owner_id,
                    StudySession.occurred_at >= since,
                    StudySession.subject_code.is_not(None),
                )
                .group_by(StudySession.subject_code)
            )
        ).all()
    )

    weight_total = sum(subject.weight_coefficient for subject in subjects)
    # Only subject-tagged time counts toward shares, so an untagged session
    # never silently dilutes every subject's actual_share.
    seconds_total = sum(totals.get(subject.code, 0) for subject in subjects)

    allocation = []
    for subject in subjects:
        planned = subject.weight_coefficient / weight_total if weight_total else 0.0
        actual_seconds = int(totals.get(subject.code, 0))
        actual = actual_seconds / seconds_total if seconds_total else 0.0
        allocation.append(
            SubjectAllocationRead(
                subject_code=subject.code,
                name_el=subject.name_el,
                name_en=subject.name_en,
                weight_coefficient=subject.weight_coefficient,
                planned_share=planned,
                actual_seconds=actual_seconds,
                actual_share=actual,
                delta=actual - planned,
            )
        )
    return allocation
