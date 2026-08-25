import asyncio
import json
import logging
from datetime import UTC, datetime

from pywebpush import WebPushException, webpush
from sqlalchemy import text
from sqlmodel import select

from app.core.config import settings
from app.core.db import async_session_maker
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
        due_tasks = await db.scalars(
            select(Task).where(
                Task.due_date <= now,
                Task.due_date.is_not(None),
                Task.notified_at.is_(None),
                Task.status != TaskStatus.DONE,
            )
        )

        for task in due_tasks:
            subscriptions = await push_subscription_service.list_subscriptions_for_user(
                db, task.owner_id
            )
            payload = json.dumps({"title": "Task due", "body": task.title, "task_id": str(task.id)})

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
                        logger.warning("Failed to send push notification: %s", exc)

            task.notified_at = now

        await db.commit()
