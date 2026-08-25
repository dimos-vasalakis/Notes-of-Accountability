from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models.push_subscription import PushSubscription
from app.models.user import User
from app.schemas.push_subscription import (
    PushSubscriptionCreate,
    PushSubscriptionDelete,
    PushSubscriptionRead,
)
from app.services import push_subscription_service

router = APIRouter(prefix="/api/push-subscriptions", tags=["push-subscriptions"])


@router.post("", response_model=PushSubscriptionRead, status_code=status.HTTP_201_CREATED)
async def create_subscription(
    data: PushSubscriptionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PushSubscription:
    return await push_subscription_service.create_or_update_subscription(
        db, current_user.id, data
    )


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def delete_subscription(
    data: PushSubscriptionDelete,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await push_subscription_service.delete_subscription(db, current_user.id, data.endpoint)
