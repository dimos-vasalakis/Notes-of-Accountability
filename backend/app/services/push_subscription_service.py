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
    result = await db.scalars(
        select(PushSubscription).where(PushSubscription.user_id == user_id)
    )
    return list(result)


async def list_subscriptions_for_users(
    db: AsyncSession, user_ids: list[uuid.UUID]
) -> dict[uuid.UUID, list[PushSubscription]]:
    if not user_ids:
        return {}

    result = await db.scalars(
        select(PushSubscription).where(PushSubscription.user_id.in_(user_ids))
    )
    subscriptions_by_user: dict[uuid.UUID, list[PushSubscription]] = defaultdict(list)
    for subscription in result:
        subscriptions_by_user[subscription.user_id].append(subscription)
    return subscriptions_by_user
