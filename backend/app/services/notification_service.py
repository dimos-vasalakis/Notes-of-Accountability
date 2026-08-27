import asyncio
import json
import logging
from datetime import UTC, datetime, timedelta

from pywebpush import WebPushException, webpush
from sqlalchemy import and_, func, or_, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.config import settings
from app.core.db import async_session_maker
from app.models.push_subscription import PushSubscription
from app.models.task import Task, TaskStatus
from app.services import pod_service, push_subscription_service

logger = logging.getLogger(__name__)

# Arbitrary fixed keys: guard each job so only one worker/process runs it at a
# time. Distinct keys so the two jobs never block each other.
_ADVISORY_LOCK_KEY = 928374839123
_POD_NUDGE_LOCK_KEY = 514820397461

# How long a pod member must be silent before their pod-mates are nudged, and
# how long before the same member can trigger another nudge.
POD_INACTIVITY_HOURS = 24
POD_NUDGE_COOLDOWN_HOURS = 24


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
                            Task.due_date - func.make_interval(0, 0, 0, 0, 0, Task.reminder_minutes_before)
                            <= now,
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


async def send_pod_inactivity_nudges() -> None:
    """Tell a pod when one of its members has gone quiet, so they can nudge them."""
    if not settings.vapid_public_key or not settings.vapid_private_key:
        return

    async with async_session_maker() as db:
        got_lock = await db.scalar(
            text("SELECT pg_try_advisory_xact_lock(:key)"), {"key": _POD_NUDGE_LOCK_KEY}
        )
        if not got_lock:
            return

        now = datetime.now(UTC)
        quiet = await pod_service.list_quiet_memberships(
            db,
            inactivity_threshold=now - timedelta(hours=POD_INACTIVITY_HOURS),
            nudge_cooldown=now - timedelta(hours=POD_NUDGE_COOLDOWN_HOURS),
        )

        for membership, user in quiet:
            recipient_ids = await pod_service.list_other_member_ids(
                db, membership.pod_id, membership.user_id
            )
            if not recipient_ids:
                # A pod of one has nobody to nudge; still stamp the membership
                # so it doesn't get re-examined every tick.
                membership.last_nudge_sent_at = now
                continue

            subscriptions_by_user = (
                await push_subscription_service.list_subscriptions_for_users(
                    db, recipient_ids
                )
            )
            subscriptions = [
                subscription
                for user_id in recipient_ids
                for subscription in subscriptions_by_user.get(user_id, [])
            ]

            name = pod_service.display_name_for(user)
            payload = json.dumps(
                {
                    "title": "Pod check-in",
                    "body": f"{name} has gone quiet for {POD_INACTIVITY_HOURS}h — nudge them!",
                }
            )
            if await _send_to_subscriptions(db, subscriptions, payload):
                membership.last_nudge_sent_at = now

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
