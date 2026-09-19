"""Exam-track configuration, subject lists, and study-session tracking for student mode."""

import uuid
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.cache import (
    EXAM_REF_SCOPE,
    STUDY_SCOPE,
    bump_version,
    get_json,
    get_version,
    set_json,
)
from app.core.exceptions import NotFoundError
from app.models.exam_prep import ExamConfig, ExamSubject, StudySession
from app.schemas.exam_prep import (
    ExamConfigRead,
    ExamSubjectRead,
    StudySessionCreate,
    StudySessionRead,
    SubjectAllocationRead,
)

WINDOW_DAYS = {"week": 7, "month": 30}


def window_start(window: str) -> datetime:
    """Convert a "week"/"month" window label into its starting timestamp."""
    return datetime.now(UTC) - timedelta(days=WINDOW_DAYS[window])


async def invalidate_exam_reference_cache(track: str) -> None:
    """Orphan a track's cached config/subjects. Called by scripts/seed_exam_config.py,
    the only writer of this data; without it the cache just ages out via TTL.
    """
    await bump_version(EXAM_REF_SCOPE, track)


async def _invalidate_study_cache(owner_id: uuid.UUID) -> None:
    """Orphan the owner's cached sessions/allocation. Streaks share this version."""
    await bump_version(STUDY_SCOPE, owner_id)


async def get_exam_config(db: AsyncSession, track: str) -> ExamConfigRead:
    """Fetch the active exam configuration for a track. Cache-aside over Redis.

    Only the stored fields are cached; `days_remaining` is recomputed on every
    call so the countdown never goes stale across midnight.
    """
    version = await get_version(EXAM_REF_SCOPE, track)
    cache_key = f"exam:config:{track}:v{version}"
    cached = await get_json(cache_key)
    if cached is None:
        config = await db.scalar(
            select(ExamConfig).where(
                ExamConfig.track == track, ExamConfig.is_active.is_(True)
            )
        )
        if config is None:
            raise NotFoundError(f"No exam configuration found for track '{track}'")
        cached = {
            "track": config.track,
            "academic_year": config.academic_year,
            "exam_date": config.exam_date.isoformat(),
        }
        await set_json(cache_key, cached)

    exam_date = date.fromisoformat(cached["exam_date"])
    return ExamConfigRead(
        track=cached["track"],
        academic_year=cached["academic_year"],
        exam_date=exam_date,
        days_remaining=days_remaining(exam_date),
    )


def days_remaining(exam_date: date, as_of: date | None = None) -> int:
    """Days until the first exam. Negative once the exams have passed."""
    return (exam_date - (as_of or datetime.now(UTC).date())).days


async def list_subjects(db: AsyncSession, track: str) -> list[ExamSubjectRead]:
    """List the active subjects for a track, in display order. Cache-aside over Redis."""
    version = await get_version(EXAM_REF_SCOPE, track)
    cache_key = f"exam:subjects:{track}:v{version}"
    cached = await get_json(cache_key)
    if cached is not None:
        return [ExamSubjectRead.model_validate(item) for item in cached]

    result = await db.scalars(
        select(ExamSubject)
        .where(ExamSubject.track == track, ExamSubject.is_active.is_(True))
        .order_by(ExamSubject.display_order)
    )
    subjects = [ExamSubjectRead.model_validate(subject) for subject in result]
    await set_json(cache_key, [subject.model_dump(mode="json") for subject in subjects])
    return subjects


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
    await _invalidate_study_cache(owner_id)
    return session


async def list_study_sessions(
    db: AsyncSession, owner_id: uuid.UUID, window: str
) -> list[StudySessionRead]:
    """List a user's study sessions in a "week"/"month" window, most recent first.

    Cache-aside over Redis. The window is a sliding one, so an entry can keep
    a session that has just aged out for up to the cache TTL.
    """
    version = await get_version(STUDY_SCOPE, owner_id)
    cache_key = f"study:sessions:{owner_id}:v{version}:{window}"
    cached = await get_json(cache_key)
    if cached is not None:
        return [StudySessionRead.model_validate(item) for item in cached]

    result = await db.scalars(
        select(StudySession)
        .where(
            StudySession.owner_id == owner_id,
            StudySession.occurred_at >= window_start(window),
        )
        .order_by(StudySession.occurred_at.desc())
    )
    sessions = [StudySessionRead.model_validate(session) for session in result]
    await set_json(cache_key, [session.model_dump(mode="json") for session in sessions])
    return sessions


async def get_subject_allocation(
    db: AsyncSession, owner_id: uuid.UUID, track: str, window: str
) -> list[SubjectAllocationRead]:
    """Compare each subject's weight-derived target share against time actually spent.

    Cache-aside over Redis, keyed on both the owner's study version and the
    track's reference-data version (subject weights feed the shares). Like the
    session list, the sliding window can keep just-aged-out time for up to the TTL.
    """
    subjects = await list_subjects(db, track)
    if not subjects:
        return []

    study_version = await get_version(STUDY_SCOPE, owner_id)
    ref_version = await get_version(EXAM_REF_SCOPE, track)
    cache_key = f"study:allocation:{owner_id}:{track}:v{study_version}.{ref_version}:{window}"
    cached = await get_json(cache_key)
    if cached is not None:
        return [SubjectAllocationRead.model_validate(item) for item in cached]

    since = window_start(window)

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
    await set_json(cache_key, [item.model_dump(mode="json") for item in allocation])
    return allocation
