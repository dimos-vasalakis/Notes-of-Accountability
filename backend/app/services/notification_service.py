import asyncio
import json
import logging
from datetime import UTC, datetime, timedelta

from pywebpush import WebPushException, webpush
from sqlalchemy import and_, or_, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.config import settings
from app.core.db import async_session_maker
from app.models.push_subscription import PushSubscription
from app.models.task import Task, TaskStatus
from app.services import push_subscription_service

logger = logging.getLogger(__name__)

# Arbitrary fixed key: guards this job so only one worker/process runs it at a time.
_ADVISORY_LOCK_KEY = 928374839123


async def send_due_task_notifications() -> None:
    if not settings.vapid_public_key or not settings.vapid_private_key:
        return

    async with async_session_maker() as db:
        got_lock = await db.scalar(text("SELECT pg_try_advisory_xact_lock(:key)"), {"key": _ADVISORY_LOCK_KEY})
        if not got_lock:
            return

        now = datetime.now(UTC)
        candidate_tasks = list(
            await db.scalars(
                select(Task).where(
                    Task.due_date.is_not(None),
                    Task.status != TaskStatus.DONE,
                    or_(
                        and_(Task.notified_at.is_(None), Task.due_date <= now),
                        and_(
                            Task.reminder_notified_at.is_(None),
                            Task.reminder_minutes_before.is_not(None),
                        ),
                    ),
                )
            )
        )

        subscriptions_by_owner = await push_subscription_service.list_subscriptions_for_users(
            db, [task.owner_id for task in candidate_tasks]
        )

        for task in candidate_tasks:
            due_fire = task.notified_at is None and task.due_date <= now
            lead_fire = (
                task.reminder_notified_at is None
                and task.reminder_minutes_before is not None
                and (task.due_date - timedelta(minutes=task.reminder_minutes_before)) <= now
            )
            if not due_fire and not lead_fire:
                continue

            subscriptions = subscriptions_by_owner.get(task.owner_id, [])

            if due_fire:
                payload = json.dumps({"title": "Task due", "body": task.title, "task_id": str(task.id)})
                if await _send_to_subscriptions(db, subscriptions, payload):
                    task.notified_at = now

            if lead_fire:
                payload = json.dumps(
                    {
                        "title": "Task due soon",
                        "body": f"{task.title} — due in {task.reminder_minutes_before} minutes",
                        "task_id": str(task.id),
                    }
                )
                if await _send_to_subscriptions(db, subscriptions, payload):
                    task.reminder_notified_at = now

        await db.commit()


async def _send_to_subscriptions(
    db: AsyncSession, subscriptions: list[PushSubscription], payload: str
) -> bool:
    """Send `payload` to every subscription; returns True iff none failed (excluding prunes)."""
    any_failed = False
    for subscription in subscriptions:
        try:
            await asyncio.to_thread(
                webpush,
                subscription_info={
                    "endpoint": subscription.endpoint,
                    "keys": {
                        "p256dh": subscription.p256dh,
                        "auth": subscription.auth,
                    },
                },
                data=payload,
                vapid_private_key=settings.vapid_private_key,
                vapid_claims={"sub": settings.vapid_subject},
            )
        except WebPushException as exc:
            if exc.response is not None and exc.response.status_code in (404, 410):
                await db.delete(subscription)
            else:
                any_failed = True
                logger.warning("Failed to send push notification: %s", exc)
        except Exception:
            any_failed = True
            logger.exception("Unexpected error sending push notification")
    return not any_failed
