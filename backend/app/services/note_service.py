import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.exceptions import NotFoundError
from app.models.note import Note
from app.schemas.note import NoteCreate, NoteUpdate


async def create_note(db: AsyncSession, owner_id: uuid.UUID, data: NoteCreate) -> Note:
    note = Note(owner_id=owner_id, title=data.title, content=data.content)
    db.add(note)
    await db.commit()
    await db.refresh(note)
    return note


async def list_notes(db: AsyncSession, owner_id: uuid.UUID) -> list[Note]:
    result = await db.scalars(select(Note).where(Note.owner_id == owner_id))
    return list(result)


async def get_note(db: AsyncSession, owner_id: uuid.UUID, note_id: uuid.UUID) -> Note:
    note = await db.scalar(
        select(Note).where(Note.id == note_id, Note.owner_id == owner_id)
    )
    if note is None:
        raise NotFoundError("Note not found")
    return note


async def update_note(
    db: AsyncSession, owner_id: uuid.UUID, note_id: uuid.UUID, data: NoteUpdate
) -> Note:
    note = await get_note(db, owner_id, note_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(note, field, value)
    await db.commit()
    await db.refresh(note)
    return note


async def delete_note(db: AsyncSession, owner_id: uuid.UUID, note_id: uuid.UUID) -> None:
    note = await get_note(db, owner_id, note_id)
    await db.delete(note)
    await db.commit()
