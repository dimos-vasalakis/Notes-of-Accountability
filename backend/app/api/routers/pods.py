import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models.user import User
from app.schemas.pod import PodCreate, PodFeedRead, PodJoin, PodRead, StreakRead
from app.services import pod_service

router = APIRouter(prefix="/api/pods", tags=["pods"])


@router.post("", response_model=PodRead, status_code=status.HTTP_201_CREATED)
async def create_pod(
    data: PodCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PodRead:
    return await pod_service.create_pod(db, current_user.id, data.name)


@router.post("/join", response_model=PodRead)
async def join_pod(
    data: PodJoin,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PodRead:
    return await pod_service.join_pod(db, current_user.id, data.invite_code)


@router.get("", response_model=list[PodRead])
async def list_pods(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[PodRead]:
    return await pod_service.list_my_pods(db, current_user.id)


# Declared before /{pod_id} so the dynamic segment doesn't swallow "me".
@router.get("/me/streak", response_model=StreakRead)
async def my_streak(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StreakRead:
    return await pod_service.compute_streak(db, current_user.id)


@router.get("/{pod_id}/feed", response_model=PodFeedRead)
async def get_pod_feed(
    pod_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PodFeedRead:
    return await pod_service.get_pod_feed(db, pod_id, current_user.id)


@router.delete("/{pod_id}/members/me", status_code=status.HTTP_204_NO_CONTENT)
async def leave_pod(
    pod_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await pod_service.leave_pod(db, current_user.id, pod_id)
