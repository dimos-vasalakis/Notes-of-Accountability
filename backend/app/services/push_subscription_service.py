"""Manages web push subscriptions so notifications can be delivered to a user's devices."""

import uuid
from collections import defaultdict

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.push_subscription import PushSubscription
from app.schemas.push_subscription import PushSubscriptionCreate


async def create_or_update_subscription(
    db: AsyncSession, user_id: uuid.UUID, data: PushSubscriptionCreate
) -> PushSubscription:
    """Upsert a push subscription, rotating keys if the endpoint is already known."""
    existing = await db.scalar(
        select(PushSubscription).where(
            PushSubscription.endpoint == data.endpoint,
            PushSubscription.user_id == user_id,
        )
    )
    if existing is not None:
        existing.p256dh = data.keys.p256dh
        existing.auth = data.keys.auth
        await db.commit()
        await db.refresh(existing)
        return existing

    # Endpoint may belong to a stale subscription from another user; clear it first.
    await db.execute(
        delete(PushSubscription).where(PushSubscription.endpoint == data.endpoint)
    )

    subscription = PushSubscription(
        user_id=user_id,
        endpoint=data.endpoint,
        p256dh=data.keys.p256dh,
        auth=data.keys.auth,
    )
    db.add(subscription)
    await db.commit()
    await db.refresh(subscription)
    return subscription


async def delete_subscription(db: AsyncSession, user_id: uuid.UUID, endpoint: str) -> None:
    """Remove a subscription by endpoint, scoped to its owning user."""
    subscription = await db.scalar(
        select(PushSubscription).where(
            PushSubscription.endpoint == endpoint, PushSubscription.user_id == user_id
        )
    )
    if subscription is not None:
        await db.delete(subscription)
        await db.commit()


async def list_subscriptions_for_user(
    db: AsyncSession, user_id: uuid.UUID
) -> list[PushSubscription]:
    """Return every push subscription registered for a single user."""
    result = await db.scalars(
        select(PushSubscription).where(PushSubscription.user_id == user_id)
    )
    return list(result)


async def list_subscriptions_for_users(
    db: AsyncSession, user_ids: list[uuid.UUID]
) -> dict[uuid.UUID, list[PushSubscription]]:
    """Batch-fetch subscriptions for multiple users, grouped by user id."""
    if not user_ids:
        return {}

    result = await db.scalars(
        select(PushSubscription).where(PushSubscription.user_id.in_(user_ids))
    )
    subscriptions_by_user: dict[uuid.UUID, list[PushSubscription]] = defaultdict(list)
    for subscription in result:
        subscriptions_by_user[subscription.user_id].append(subscription)
    return subscriptions_by_user
