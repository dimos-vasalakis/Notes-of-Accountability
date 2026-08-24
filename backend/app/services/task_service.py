import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.exceptions import NotFoundError
from app.models.task import Task, TaskStatus
from app.schemas.task import TaskCreate, TaskUpdate


async def create_task(db: AsyncSession, owner_id: uuid.UUID, data: TaskCreate) -> Task:
    task = Task(
        owner_id=owner_id,
        title=data.title,
        description=data.description,
        due_date=data.due_date,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


async def list_tasks(
    db: AsyncSession, owner_id: uuid.UUID, status: TaskStatus | None = None
) -> list[Task]:
    query = select(Task).where(Task.owner_id == owner_id)
    if status is not None:
        query = query.where(Task.status == status)
    result = await db.scalars(query)
    return list(result)


async def get_task(db: AsyncSession, owner_id: uuid.UUID, task_id: uuid.UUID) -> Task:
    task = await db.scalar(
        select(Task).where(Task.id == task_id, Task.owner_id == owner_id)
    )
    if task is None:
        raise NotFoundError("Task not found")
    return task


async def update_task(
    db: AsyncSession, owner_id: uuid.UUID, task_id: uuid.UUID, data: TaskUpdate
) -> Task:
    task = await get_task(db, owner_id, task_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(task, field, value)
    await db.commit()
    await db.refresh(task)
    return task


async def delete_task(db: AsyncSession, owner_id: uuid.UUID, task_id: uuid.UUID) -> None:
    task = await get_task(db, owner_id, task_id)
    await db.delete(task)
    await db.commit()
