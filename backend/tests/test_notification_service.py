from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.push_subscription import PushSubscription
from app.models.task import Task
from app.models.user import User
from app.services import notification_service


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
