import uuid
from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.exam_prep import StudySession
from app.models.pod import PodMembership
from app.models.task import Task, TaskStatus
from app.models.user import User
from app.services import pod_service

USER_A = {"email": "pod-owner@example.com", "password": "supersecret1"}
USER_B = {"email": "pod-mate@example.com", "password": "supersecret1"}

TODAY = datetime.now(UTC).date()


async def _make_user(db: AsyncSession, email: str) -> User:
    user = User(email=email, hashed_password="x")
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def _complete_task_on(db: AsyncSession, user_id: uuid.UUID, days_ago: int) -> None:
    when = datetime.now(UTC) - timedelta(days=days_ago)
    db.add(
        Task(
            owner_id=user_id,
            title=f"done-{days_ago}",
            status=TaskStatus.DONE,
            completed_at=when,
        )
    )
    await db.commit()


async def _study_on(db: AsyncSession, user_id: uuid.UUID, days_ago: int) -> None:
    db.add(
        StudySession(
            owner_id=user_id,
            subject_code=None,
            duration_seconds=1500,
            occurred_at=datetime.now(UTC) - timedelta(days=days_ago),
        )
    )
    await db.commit()


# --- streak correctness ----------------------------------------------------


async def test_streak_is_zero_without_activity(db_session: AsyncSession) -> None:
    user = await _make_user(db_session, "streak-none@example.com")

    streak = await pod_service.compute_streak(db_session, user.id)

    assert streak.current_streak == 0
    assert streak.active_today is False
    assert streak.last_active_at is None


async def test_completed_task_today_starts_streak(db_session: AsyncSession) -> None:
    user = await _make_user(db_session, "streak-today@example.com")
    await _complete_task_on(db_session, user.id, days_ago=0)

    streak = await pod_service.compute_streak(db_session, user.id)

    assert streak.current_streak == 1
    assert streak.active_today is True


async def test_study_session_alone_counts_as_activity(db_session: AsyncSession) -> None:
    user = await _make_user(db_session, "streak-study@example.com")
    await _study_on(db_session, user.id, days_ago=0)

    streak = await pod_service.compute_streak(db_session, user.id)

    assert streak.current_streak == 1
    assert streak.active_today is True


async def test_streak_survives_a_today_that_has_not_started_yet(
    db_session: AsyncSession,
) -> None:
    """Yesterday + the day before, nothing today: the streak must not reset."""
    user = await _make_user(db_session, "streak-morning@example.com")
    await _complete_task_on(db_session, user.id, days_ago=1)
    await _complete_task_on(db_session, user.id, days_ago=2)

    streak = await pod_service.compute_streak(db_session, user.id)

    assert streak.current_streak == 2
    assert streak.active_today is False


async def test_gap_day_resets_streak(db_session: AsyncSession) -> None:
    user = await _make_user(db_session, "streak-gap@example.com")
    await _complete_task_on(db_session, user.id, days_ago=0)
    # Nothing on day 1 -- the run stops here.
    await _complete_task_on(db_session, user.id, days_ago=2)
    await _complete_task_on(db_session, user.id, days_ago=3)

    streak = await pod_service.compute_streak(db_session, user.id)

    assert streak.current_streak == 1


async def test_two_activities_same_day_count_once(db_session: AsyncSession) -> None:
    user = await _make_user(db_session, "streak-dupe@example.com")
    await _complete_task_on(db_session, user.id, days_ago=0)
    await _study_on(db_session, user.id, days_ago=0)

    streak = await pod_service.compute_streak(db_session, user.id)

    assert streak.current_streak == 1


async def test_uncompleting_a_task_removes_the_streak_day(client: AsyncClient) -> None:
    await client.post("/api/auth/signup", json=USER_A)
    task = (await client.post("/api/tasks", json={"title": "Revise"})).json()

    await client.patch(f"/api/tasks/{task['id']}", json={"status": "done"})
    assert (await client.get("/api/pods/me/streak")).json()["current_streak"] == 1

    await client.patch(f"/api/tasks/{task['id']}", json={"status": "todo"})
    streak = (await client.get("/api/pods/me/streak")).json()
    assert streak["current_streak"] == 0
    assert streak["active_today"] is False


# --- pod lifecycle ---------------------------------------------------------


async def test_pods_require_authentication(client: AsyncClient) -> None:
    assert (await client.get("/api/pods")).status_code == 401


async def test_create_and_list_pod(client: AsyncClient) -> None:
    await client.post("/api/auth/signup", json=USER_A)

    response = await client.post("/api/pods", json={"name": "Panelladikes 2027"})

    assert response.status_code == 201
    pod = response.json()
    assert pod["name"] == "Panelladikes 2027"
    assert pod["member_count"] == 1
    assert len(pod["invite_code"]) == 8

    listed = (await client.get("/api/pods")).json()
    assert [p["id"] for p in listed] == [pod["id"]]


async def test_join_pod_with_invite_code(client: AsyncClient) -> None:
    await client.post("/api/auth/signup", json=USER_A)
    pod = (await client.post("/api/pods", json={"name": "Study squad"})).json()
    await client.post("/api/auth/logout")

    await client.post("/api/auth/signup", json=USER_B)
    joined = await client.post("/api/pods/join", json={"invite_code": pod["invite_code"]})

    assert joined.status_code == 200
    assert joined.json()["member_count"] == 2


async def test_join_is_case_insensitive_and_trimmed(client: AsyncClient) -> None:
    await client.post("/api/auth/signup", json=USER_A)
    pod = (await client.post("/api/pods", json={"name": "Squad"})).json()
    await client.post("/api/auth/logout")

    await client.post("/api/auth/signup", json=USER_B)
    response = await client.post(
        "/api/pods/join", json={"invite_code": f"  {pod['invite_code'].lower()}  "}
    )

    assert response.status_code == 200


async def test_join_unknown_code_is_404(client: AsyncClient) -> None:
    await client.post("/api/auth/signup", json=USER_A)

    response = await client.post("/api/pods/join", json={"invite_code": "ZZZZZZZZ"})

    assert response.status_code == 404


async def test_joining_twice_conflicts(client: AsyncClient) -> None:
    await client.post("/api/auth/signup", json=USER_A)
    pod = (await client.post("/api/pods", json={"name": "Squad"})).json()

    response = await client.post("/api/pods/join", json={"invite_code": pod["invite_code"]})

    assert response.status_code == 409


async def test_feed_shows_every_member_with_streaks(client: AsyncClient) -> None:
    await client.post("/api/auth/signup", json=USER_A)
    pod = (await client.post("/api/pods", json={"name": "Squad"})).json()
    await client.post("/api/auth/logout")

    await client.post("/api/auth/signup", json=USER_B)
    await client.post("/api/pods/join", json={"invite_code": pod["invite_code"]})
    task = (await client.post("/api/tasks", json={"title": "Maths"})).json()
    await client.patch(f"/api/tasks/{task['id']}", json={"status": "done"})

    feed = (await client.get(f"/api/pods/{pod['id']}/feed")).json()

    assert feed["pod"]["member_count"] == 2
    by_name = {m["display_name"]: m for m in feed["members"]}
    assert by_name["pod-mate"]["current_streak"] == 1
    assert by_name["pod-mate"]["active_today"] is True
    assert by_name["pod-owner"]["current_streak"] == 0
    # Active members sort first.
    assert feed["members"][0]["display_name"] == "pod-mate"


async def test_feed_never_exposes_member_emails(client: AsyncClient) -> None:
    await client.post("/api/auth/signup", json=USER_A)
    pod = (await client.post("/api/pods", json={"name": "Squad"})).json()

    body = (await client.get(f"/api/pods/{pod['id']}/feed")).text

    assert USER_A["email"] not in body


async def test_non_member_cannot_read_feed(client: AsyncClient) -> None:
    await client.post("/api/auth/signup", json=USER_A)
    pod = (await client.post("/api/pods", json={"name": "Private"})).json()
    await client.post("/api/auth/logout")

    await client.post("/api/auth/signup", json=USER_B)
    response = await client.get(f"/api/pods/{pod['id']}/feed")

    assert response.status_code == 404


async def test_leave_pod(client: AsyncClient) -> None:
    await client.post("/api/auth/signup", json=USER_A)
    pod = (await client.post("/api/pods", json={"name": "Squad"})).json()

    assert (await client.delete(f"/api/pods/{pod['id']}/members/me")).status_code == 204
    assert (await client.get("/api/pods")).json() == []
    assert (await client.get(f"/api/pods/{pod['id']}/feed")).status_code == 404


# --- nudge candidate selection --------------------------------------------


async def _backdate_memberships(
    db_session: AsyncSession, pod_id: uuid.UUID, *, days: int
) -> None:
    """Age a pod's memberships so its members are eligible to be nudged."""
    memberships = await db_session.scalars(
        select(PodMembership).where(PodMembership.pod_id == pod_id)
    )
    for membership in memberships:
        membership.joined_at = datetime.now(UTC) - timedelta(days=days)
    await db_session.commit()


async def test_member_who_just_joined_is_not_reported_as_quiet(
    db_session: AsyncSession,
) -> None:
    fresh = await _make_user(db_session, "fresh-join@example.com")
    pod = await pod_service.create_pod(db_session, fresh.id, "Squad")
    assert pod is not None

    now = datetime.now(UTC)
    result = await pod_service.list_quiet_memberships(
        db_session,
        inactivity_threshold=now - timedelta(hours=24),
        nudge_cooldown=now - timedelta(hours=24),
    )

    assert result == []


async def test_quiet_member_is_flagged_and_active_member_is_not(
    db_session: AsyncSession,
) -> None:
    quiet = await _make_user(db_session, "quiet@example.com")
    active = await _make_user(db_session, "active@example.com")
    pod = await pod_service.create_pod(db_session, quiet.id, "Squad")
    await pod_service.join_pod(db_session, active.id, pod.invite_code)
    await _complete_task_on(db_session, active.id, days_ago=0)
    await _backdate_memberships(db_session, pod.id, days=3)

    now = datetime.now(UTC)
    result = await pod_service.list_quiet_memberships(
        db_session,
        inactivity_threshold=now - timedelta(hours=24),
        nudge_cooldown=now - timedelta(hours=24),
    )

    assert [user.id for _, user in result] == [quiet.id]


async def test_recently_nudged_member_is_skipped(db_session: AsyncSession) -> None:
    quiet = await _make_user(db_session, "quiet-nudged@example.com")
    pod = await pod_service.create_pod(db_session, quiet.id, "Squad")

    now = datetime.now(UTC)
    membership = await db_session.scalar(
        select(pod_service.PodMembership).where(
            pod_service.PodMembership.pod_id == pod.id
        )
    )
    membership.last_nudge_sent_at = now - timedelta(hours=1)
    await db_session.commit()

    result = await pod_service.list_quiet_memberships(
        db_session,
        inactivity_threshold=now - timedelta(hours=24),
        nudge_cooldown=now - timedelta(hours=24),
    )

    assert result == []
