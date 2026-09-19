"""CRUD operations for tasks, including the bookkeeping around completion and reminders."""

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.cache import TASKS_SCOPE, bump_version, get_json, get_version, set_json
from app.core.exceptions import NotFoundError
from app.models.task import Task, TaskStatus
from app.schemas.task import TaskCreate, TaskRead, TaskUpdate


def _list_cache_key(owner_id: uuid.UUID, status: TaskStatus | None, version: int) -> str:
    return f"tasks:list:{owner_id}:v{version}:{status.value if status else 'all'}"


def _item_cache_key(owner_id: uuid.UUID, task_id: uuid.UUID, version: int) -> str:
    return f"tasks:item:{owner_id}:v{version}:{task_id}"


async def _invalidate_task_cache(owner_id: uuid.UUID) -> None:
    """Orphan the owner's cached task lists/items (see app.core.cache versioning).

    Task completion also feeds streaks, which are keyed on this same version.
    """
    await bump_version(TASKS_SCOPE, owner_id)


async def _get_owned_task(db: AsyncSession, owner_id: uuid.UUID, task_id: uuid.UUID) -> Task:
    """Fetch the live ORM row for a task, raising if it doesn't exist or isn't owned by the user."""
    task = await db.scalar(
        select(Task).where(Task.id == task_id, Task.owner_id == owner_id)
    )
    if task is None:
        raise NotFoundError("Task not found")
    return task


async def create_task(db: AsyncSession, owner_id: uuid.UUID, data: TaskCreate) -> Task:
    """Create a new task owned by the given user."""
    task = Task(
        owner_id=owner_id,
        title=data.title,
        description=data.description,
        due_date=data.due_date,
        reminder_minutes_before=data.reminder_minutes_before,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    await _invalidate_task_cache(owner_id)
    return task


async def list_tasks(
    db: AsyncSession, owner_id: uuid.UUID, status: TaskStatus | None = None
) -> list[TaskRead]:
    """List a user's tasks, optionally narrowed to a single status. Cache-aside over Redis."""
    version = await get_version(TASKS_SCOPE, owner_id)
    cache_key = _list_cache_key(owner_id, status, version)
    cached = await get_json(cache_key)
    if cached is not None:
        return [TaskRead.model_validate(item) for item in cached]

    query = select(Task).where(Task.owner_id == owner_id)
    if status is not None:
        query = query.where(Task.status == status)
    result = await db.scalars(query)
    tasks = [TaskRead.model_validate(task) for task in result]

    await set_json(cache_key, [task.model_dump(mode="json") for task in tasks])
    return tasks


async def get_task(db: AsyncSession, owner_id: uuid.UUID, task_id: uuid.UUID) -> TaskRead:
    """Fetch a single task by id, raising if it doesn't exist or isn't owned by the user."""
    version = await get_version(TASKS_SCOPE, owner_id)
    cache_key = _item_cache_key(owner_id, task_id, version)
    cached = await get_json(cache_key)
    if cached is not None:
        return TaskRead.model_validate(cached)

    task = await _get_owned_task(db, owner_id, task_id)
    read = TaskRead.model_validate(task)
    await set_json(cache_key, read.model_dump(mode="json"))
    return read


async def update_task(
    db: AsyncSession, owner_id: uuid.UUID, task_id: uuid.UUID, data: TaskUpdate
) -> Task:
    """Apply a partial update to a task, resetting reminder/completion state as needed."""
    task = await _get_owned_task(db, owner_id, task_id)
    updates = data.model_dump(exclude_unset=True)
    # Stamp/clear completion so streaks have a reliable "done on day X" signal.
    if "status" in updates and updates["status"] != task.status:
        task.completed_at = (
            datetime.now(UTC) if updates["status"] == TaskStatus.DONE else None
        )
    if "due_date" in updates and updates["due_date"] != task.due_date:
        task.notified_at = None
        task.reminder_notified_at = None
    elif (
        "reminder_minutes_before" in updates
        and updates["reminder_minutes_before"] != task.reminder_minutes_before
    ):
        task.reminder_notified_at = None
    for field, value in updates.items():
        setattr(task, field, value)
    await db.commit()
    await db.refresh(task)
    await _invalidate_task_cache(owner_id)
    return task


async def delete_task(db: AsyncSession, owner_id: uuid.UUID, task_id: uuid.UUID) -> None:
    """Delete a task owned by the given user."""
    task = await _get_owned_task(db, owner_id, task_id)
    await db.delete(task)
    await db.commit()
    await _invalidate_task_cache(owner_id)
