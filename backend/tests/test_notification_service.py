import json
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.pod import PodMembership
from app.models.push_subscription import PushSubscription
from app.models.task import Task, TaskStatus
from app.models.user import User
from app.services import notification_service, pod_service


@pytest.fixture
def _patched_session_maker(db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch):
    @asynccontextmanager
    async def _ctx():
        yield db_session

    monkeypatch.setattr(notification_service, "async_session_maker", _ctx)


async def _make_user_with_task(
    db_session: AsyncSession,
    *,
    due_date: datetime,
    notified_at: datetime | None = None,
    reminder_minutes_before: int | None = None,
    reminder_notified_at: datetime | None = None,
) -> Task:
    user = User(email=f"{id(due_date)}-{id(reminder_notified_at)}@example.com", hashed_password="hashed")
    db_session.add(user)
    await db_session.flush()

    subscription = PushSubscription(
        user_id=user.id, endpoint=f"https://push.example.com/{user.id}", p256dh="p", auth="a"
    )
    db_session.add(subscription)

    task = Task(
        owner_id=user.id,
        title="Do the thing",
        due_date=due_date,
        notified_at=notified_at,
        reminder_minutes_before=reminder_minutes_before,
        reminder_notified_at=reminder_notified_at,
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)
    return task


async def test_sends_notification_for_due_task(
    db_session: AsyncSession, _patched_session_maker, monkeypatch: pytest.MonkeyPatch
) -> None:
    task = await _make_user_with_task(db_session, due_date=datetime.now(UTC) - timedelta(minutes=1))
    mock_webpush = Mock()
    monkeypatch.setattr(notification_service, "webpush", mock_webpush)

    await notification_service.send_due_task_notifications()

    mock_webpush.assert_called_once()
    await db_session.refresh(task)
    assert task.notified_at is not None


async def test_skips_task_not_yet_due(
    db_session: AsyncSession, _patched_session_maker, monkeypatch: pytest.MonkeyPatch
) -> None:
    task = await _make_user_with_task(db_session, due_date=datetime.now(UTC) + timedelta(hours=1))
    mock_webpush = Mock()
    monkeypatch.setattr(notification_service, "webpush", mock_webpush)

    await notification_service.send_due_task_notifications()

    mock_webpush.assert_not_called()
    await db_session.refresh(task)
    assert task.notified_at is None


async def test_skips_already_notified_task(
    db_session: AsyncSession, _patched_session_maker, monkeypatch: pytest.MonkeyPatch
) -> None:
    await _make_user_with_task(
        db_session,
        due_date=datetime.now(UTC) - timedelta(minutes=1),
        notified_at=datetime.now(UTC),
    )
    mock_webpush = Mock()
    monkeypatch.setattr(notification_service, "webpush", mock_webpush)

    await notification_service.send_due_task_notifications()

    mock_webpush.assert_not_called()


async def test_sends_lead_time_reminder_before_due(
    db_session: AsyncSession, _patched_session_maker, monkeypatch: pytest.MonkeyPatch
) -> None:
    task = await _make_user_with_task(
        db_session,
        due_date=datetime.now(UTC) + timedelta(minutes=5),
        reminder_minutes_before=10,
    )
    mock_webpush = Mock()
    monkeypatch.setattr(notification_service, "webpush", mock_webpush)

    await notification_service.send_due_task_notifications()

    mock_webpush.assert_called_once()
    await db_session.refresh(task)
    assert task.reminder_notified_at is not None
    assert task.notified_at is None


async def test_sends_both_due_and_lead_time_notifications_in_same_tick(
    db_session: AsyncSession, _patched_session_maker, monkeypatch: pytest.MonkeyPatch
) -> None:
    task = await _make_user_with_task(
        db_session,
        due_date=datetime.now(UTC) - timedelta(minutes=1),
        reminder_minutes_before=10,
    )
    mock_webpush = Mock()
    monkeypatch.setattr(notification_service, "webpush", mock_webpush)

    await notification_service.send_due_task_notifications()

    assert mock_webpush.call_count == 2
    await db_session.refresh(task)
    assert task.notified_at is not None
    assert task.reminder_notified_at is not None


async def test_skips_lead_time_reminder_already_sent(
    db_session: AsyncSession, _patched_session_maker, monkeypatch: pytest.MonkeyPatch
) -> None:
    await _make_user_with_task(
        db_session,
        due_date=datetime.now(UTC) + timedelta(minutes=5),
        reminder_minutes_before=10,
        reminder_notified_at=datetime.now(UTC),
    )
    mock_webpush = Mock()
    monkeypatch.setattr(notification_service, "webpush", mock_webpush)

    await notification_service.send_due_task_notifications()

    mock_webpush.assert_not_called()


# --- pod inactivity nudges -------------------------------------------------


async def _make_pod_member(
    db_session: AsyncSession, email: str, *, with_subscription: bool = True
) -> User:
    user = User(email=email, hashed_password="hashed")
    db_session.add(user)
    await db_session.flush()
    if with_subscription:
        db_session.add(
            PushSubscription(
                user_id=user.id,
                endpoint=f"https://push.example.com/{user.id}",
                p256dh="p",
                auth="a",
            )
        )
    await db_session.commit()
    await db_session.refresh(user)
    return user


async def _backdate_memberships(
    db_session: AsyncSession, pod_id, *, days: int
) -> None:
    """Age a pod's memberships so its members are eligible to be nudged."""
    memberships = await db_session.scalars(
        select(PodMembership).where(PodMembership.pod_id == pod_id)
    )
    for membership in memberships:
        membership.joined_at = datetime.now(UTC) - timedelta(days=days)
    await db_session.commit()


async def test_nudges_pod_mates_about_a_quiet_member(
    db_session: AsyncSession, _patched_session_maker, monkeypatch: pytest.MonkeyPatch
) -> None:
    quiet = await _make_pod_member(db_session, "nudge-quiet@example.com")
    mate = await _make_pod_member(db_session, "nudge-mate@example.com")
    pod = await pod_service.create_pod(db_session, quiet.id, "Squad")
    await pod_service.join_pod(db_session, mate.id, pod.invite_code)
    await _backdate_memberships(db_session, pod.id, days=3)
    # The mate is active, so only the quiet member should be reported on.
    db_session.add(
        Task(
            owner_id=mate.id,
            title="done",
            status=TaskStatus.DONE,
            completed_at=datetime.now(UTC),
        )
    )
    await db_session.commit()

    mock_webpush = Mock()
    monkeypatch.setattr(notification_service, "webpush", mock_webpush)

    await notification_service.send_pod_inactivity_nudges()

    # One push, to the active mate, about the quiet member.
    mock_webpush.assert_called_once()
    payload = json.loads(mock_webpush.call_args.kwargs["data"])
    assert "nudge-quiet" in payload["body"]
    assert mock_webpush.call_args.kwargs["subscription_info"]["endpoint"].endswith(
        str(mate.id)
    )

    membership = await db_session.scalar(
        select(PodMembership).where(
            PodMembership.pod_id == pod.id, PodMembership.user_id == quiet.id
        )
    )
    assert membership.last_nudge_sent_at is not None


async def test_does_not_nudge_about_an_active_member(
    db_session: AsyncSession, _patched_session_maker, monkeypatch: pytest.MonkeyPatch
) -> None:
    active = await _make_pod_member(db_session, "nudge-active@example.com")
    mate = await _make_pod_member(db_session, "nudge-active-mate@example.com")
    pod = await pod_service.create_pod(db_session, active.id, "Squad")
    await pod_service.join_pod(db_session, mate.id, pod.invite_code)
    for user in (active, mate):
        db_session.add(
            Task(
                owner_id=user.id,
                title="done",
                status=TaskStatus.DONE,
                completed_at=datetime.now(UTC),
            )
        )
    await db_session.commit()

    mock_webpush = Mock()
    monkeypatch.setattr(notification_service, "webpush", mock_webpush)

    await notification_service.send_pod_inactivity_nudges()

    mock_webpush.assert_not_called()


async def test_brand_new_member_is_never_accused_of_going_quiet(
    db_session: AsyncSession, _patched_session_maker, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Someone who just joined has no history -- that is not 24h of silence."""
    fresh = await _make_pod_member(db_session, "nudge-fresh@example.com")
    mate = await _make_pod_member(db_session, "nudge-fresh-mate@example.com")
    pod = await pod_service.create_pod(db_session, fresh.id, "Squad")
    await pod_service.join_pod(db_session, mate.id, pod.invite_code)

    mock_webpush = Mock()
    monkeypatch.setattr(notification_service, "webpush", mock_webpush)

    await notification_service.send_pod_inactivity_nudges()

    mock_webpush.assert_not_called()


async def test_nudge_is_debounced_across_ticks(
    db_session: AsyncSession, _patched_session_maker, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A member quiet for days must not re-nudge their pod on every tick."""
    quiet = await _make_pod_member(db_session, "nudge-debounce@example.com")
    mate = await _make_pod_member(db_session, "nudge-debounce-mate@example.com")
    pod = await pod_service.create_pod(db_session, quiet.id, "Squad")
    await pod_service.join_pod(db_session, mate.id, pod.invite_code)
    # Both joined days ago and neither has logged anything since.
    await _backdate_memberships(db_session, pod.id, days=3)

    mock_webpush = Mock()
    monkeypatch.setattr(notification_service, "webpush", mock_webpush)

    await notification_service.send_pod_inactivity_nudges()
    first_call_count = mock_webpush.call_count
    await notification_service.send_pod_inactivity_nudges()

    assert first_call_count == 2  # both members are quiet, each mate hears once
    assert mock_webpush.call_count == first_call_count


async def test_solo_pod_produces_no_push(
    db_session: AsyncSession, _patched_session_maker, monkeypatch: pytest.MonkeyPatch
) -> None:
    loner = await _make_pod_member(db_session, "nudge-solo@example.com")
    pod = await pod_service.create_pod(db_session, loner.id, "Just me")
    await _backdate_memberships(db_session, pod.id, days=3)

    mock_webpush = Mock()
    monkeypatch.setattr(notification_service, "webpush", mock_webpush)

    await notification_service.send_pod_inactivity_nudges()

    mock_webpush.assert_not_called()
