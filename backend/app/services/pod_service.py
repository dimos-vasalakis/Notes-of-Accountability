import secrets
import uuid
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import func, select as sa_select, union_all
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.exceptions import ConflictError, NotFoundError
from app.models.exam_prep import StudySession
from app.models.pod import Pod, PodMembership
from app.models.task import Task
from app.models.user import User
from app.schemas.pod import PodFeedRead, PodMemberFeedItem, PodRead, StreakRead

# How far back a streak can reach. Bounds the activity query so it stays cheap.
_MAX_STREAK_LOOKBACK_DAYS = 400
_INVITE_CODE_MAX_ATTEMPTS = 10


def display_name_for(user: User) -> str:
    """Pod-mates see a name, never the raw email address."""
    return user.display_name or user.email.split("@", 1)[0]


async def _activity_timestamps(
    db: AsyncSession, user_ids: list[uuid.UUID], since: datetime
) -> dict[uuid.UUID, list[datetime]]:
    """Every activity timestamp per user since `since`, batched across users.

    Activity = a task completed or a study session logged. One query for the
    whole batch so the pod feed and the nudge job don't fan out per member.
    """
    if not user_ids:
        return {}

    tasks = sa_select(Task.owner_id.label("user_id"), Task.completed_at.label("at")).where(
        Task.owner_id.in_(user_ids),
        Task.completed_at.is_not(None),
        Task.completed_at >= since,
    )
    sessions = sa_select(
        StudySession.owner_id.label("user_id"), StudySession.occurred_at.label("at")
    ).where(
        StudySession.owner_id.in_(user_ids),
        StudySession.occurred_at >= since,
    )

    rows = (await db.execute(union_all(tasks, sessions))).all()

    by_user: dict[uuid.UUID, list[datetime]] = {user_id: [] for user_id in user_ids}
    for user_id, at in rows:
        if at.tzinfo is None:
            at = at.replace(tzinfo=UTC)
        by_user[user_id].append(at)
    return by_user


def _streak_from_timestamps(
    timestamps: list[datetime], as_of: date
) -> tuple[int, bool, datetime | None]:
    if not timestamps:
        return 0, False, None

    active_days = {ts.astimezone(UTC).date() for ts in timestamps}
    last_active_at = max(timestamps)
    active_today = as_of in active_days

    # A day that hasn't been used yet must not read as a broken streak, so
    # start counting from yesterday when today is still empty.
    cursor = as_of if active_today else as_of - timedelta(days=1)
    streak = 0
    while cursor in active_days and streak < _MAX_STREAK_LOOKBACK_DAYS:
        streak += 1
        cursor -= timedelta(days=1)

    return streak, active_today, last_active_at


async def compute_streaks(
    db: AsyncSession, user_ids: list[uuid.UUID], as_of: date | None = None
) -> dict[uuid.UUID, tuple[int, bool, datetime | None]]:
    """Batch streak computation shared by the pod feed and the nudge job."""
    as_of = as_of or datetime.now(UTC).date()
    since = datetime.combine(
        as_of - timedelta(days=_MAX_STREAK_LOOKBACK_DAYS), datetime.min.time(), tzinfo=UTC
    )
    activity = await _activity_timestamps(db, user_ids, since)
    return {
        user_id: _streak_from_timestamps(timestamps, as_of)
        for user_id, timestamps in activity.items()
    }


async def compute_streak(
    db: AsyncSession, user_id: uuid.UUID, as_of: date | None = None
) -> StreakRead:
    streaks = await compute_streaks(db, [user_id], as_of)
    current_streak, active_today, last_active_at = streaks[user_id]
    return StreakRead(
        current_streak=current_streak,
        active_today=active_today,
        last_active_at=last_active_at,
    )


async def _generate_invite_code(db: AsyncSession) -> str:
    for _ in range(_INVITE_CODE_MAX_ATTEMPTS):
        code = secrets.token_hex(4).upper()
        exists = await db.scalar(select(Pod.id).where(Pod.invite_code == code))
        if exists is None:
            return code
    raise ConflictError("Could not allocate a unique invite code, please retry")


async def _member_count(db: AsyncSession, pod_id: uuid.UUID) -> int:
    return await db.scalar(
        select(func.count()).select_from(PodMembership).where(PodMembership.pod_id == pod_id)
    )


async def _to_pod_read(db: AsyncSession, pod: Pod) -> PodRead:
    return PodRead(
        id=pod.id,
        name=pod.name,
        invite_code=pod.invite_code,
        owner_id=pod.owner_id,
        member_count=await _member_count(db, pod.id),
        created_at=pod.created_at,
    )


async def create_pod(db: AsyncSession, owner_id: uuid.UUID, name: str) -> PodRead:
    pod = Pod(name=name, owner_id=owner_id, invite_code=await _generate_invite_code(db))
    db.add(pod)
    await db.flush()
    db.add(PodMembership(pod_id=pod.id, user_id=owner_id))
    await db.commit()
    await db.refresh(pod)
    return await _to_pod_read(db, pod)


async def join_pod(db: AsyncSession, user_id: uuid.UUID, invite_code: str) -> PodRead:
    pod = await db.scalar(
        select(Pod).where(Pod.invite_code == invite_code.strip().upper())
    )
    if pod is None:
        raise NotFoundError("No pod found with that invite code")

    db.add(PodMembership(pod_id=pod.id, user_id=user_id))
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictError("You are already a member of this pod") from exc

    return await _to_pod_read(db, pod)


async def list_my_pods(db: AsyncSession, user_id: uuid.UUID) -> list[PodRead]:
    pods = list(
        await db.scalars(
            select(Pod)
            .join(PodMembership, PodMembership.pod_id == Pod.id)
            .where(PodMembership.user_id == user_id)
            .order_by(Pod.created_at)
        )
    )
    return [await _to_pod_read(db, pod) for pod in pods]


async def get_pod_membership_or_404(
    db: AsyncSession, pod_id: uuid.UUID, user_id: uuid.UUID
) -> PodMembership:
    membership = await db.scalar(
        select(PodMembership).where(
            PodMembership.pod_id == pod_id, PodMembership.user_id == user_id
        )
    )
    if membership is None:
        raise NotFoundError("Pod not found")
    return membership


async def get_pod_feed(
    db: AsyncSession, pod_id: uuid.UUID, user_id: uuid.UUID
) -> PodFeedRead:
    await get_pod_membership_or_404(db, pod_id, user_id)
    pod = await db.get(Pod, pod_id)

    members = list(
        await db.scalars(
            select(User)
            .join(PodMembership, PodMembership.user_id == User.id)
            .where(PodMembership.pod_id == pod_id)
        )
    )
    streaks = await compute_streaks(db, [member.id for member in members])

    items = [
        PodMemberFeedItem(
            user_id=member.id,
            display_name=display_name_for(member),
            current_streak=streaks[member.id][0],
            active_today=streaks[member.id][1],
            last_active_at=streaks[member.id][2],
        )
        for member in members
    ]
    # Most disciplined first — the whole point of the feed.
    items.sort(key=lambda item: (item.active_today, item.current_streak), reverse=True)

    return PodFeedRead(pod=await _to_pod_read(db, pod), members=items)


async def leave_pod(db: AsyncSession, user_id: uuid.UUID, pod_id: uuid.UUID) -> None:
    membership = await get_pod_membership_or_404(db, pod_id, user_id)
    await db.delete(membership)
    await db.commit()


async def list_quiet_memberships(
    db: AsyncSession, inactivity_threshold: datetime, nudge_cooldown: datetime
) -> list[tuple[PodMembership, User]]:
    """Memberships whose user has been inactive since `inactivity_threshold`
    and who hasn't already triggered a nudge since `nudge_cooldown`.
    """
    rows = (
        await db.execute(
            select(PodMembership, User)
            .join(User, User.id == PodMembership.user_id)
            .where(
                # Someone can't have "gone quiet" over a window that started
                # before they joined -- without this, a member who signs up
                # and joins a pod is accused of a 24h silence on the very
                # next scheduler tick.
                PodMembership.joined_at < inactivity_threshold,
                (PodMembership.last_nudge_sent_at.is_(None))
                | (PodMembership.last_nudge_sent_at < nudge_cooldown),
            )
        )
    ).all()
    if not rows:
        return []

    activity = await _activity_timestamps(
        db, list({membership.user_id for membership, _ in rows}), inactivity_threshold
    )
    # Empty list => no activity at all since the threshold => gone quiet.
    return [
        (membership, user)
        for membership, user in rows
        if not activity.get(membership.user_id)
    ]


async def list_other_member_ids(
    db: AsyncSession, pod_id: uuid.UUID, exclude_user_id: uuid.UUID
) -> list[uuid.UUID]:
    result = await db.scalars(
        select(PodMembership.user_id).where(
            PodMembership.pod_id == pod_id, PodMembership.user_id != exclude_user_id
        )
    )
    return list(result)
