"""CRUD operations for markdown notes, always scoped to their owning user."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.cache import NOTES_SCOPE, bump_version, get_json, get_version, set_json
from app.core.exceptions import NotFoundError
from app.models.note import Note
from app.schemas.note import NoteCreate, NoteRead, NoteUpdate


def _list_cache_key(owner_id: uuid.UUID, version: int) -> str:
    return f"notes:list:{owner_id}:v{version}"


def _item_cache_key(owner_id: uuid.UUID, note_id: uuid.UUID, version: int) -> str:
    return f"notes:item:{owner_id}:v{version}:{note_id}"


async def _invalidate_note_cache(owner_id: uuid.UUID) -> None:
    """Orphan the owner's cached note lists/items (see app.core.cache versioning)."""
    await bump_version(NOTES_SCOPE, owner_id)


async def _get_owned_note(db: AsyncSession, owner_id: uuid.UUID, note_id: uuid.UUID) -> Note:
    """Fetch the live ORM row for a note, raising if it doesn't exist or isn't owned by the user."""
    note = await db.scalar(
        select(Note).where(Note.id == note_id, Note.owner_id == owner_id)
    )
    if note is None:
        raise NotFoundError("Note not found")
    return note


async def create_note(db: AsyncSession, owner_id: uuid.UUID, data: NoteCreate) -> Note:
    """Persist a new note owned by the given user."""
    note = Note(owner_id=owner_id, title=data.title, content=data.content)
    db.add(note)
    await db.commit()
    await db.refresh(note)
    await _invalidate_note_cache(owner_id)
    return note


async def list_notes(db: AsyncSession, owner_id: uuid.UUID) -> list[NoteRead]:
    """Return every note belonging to the given user. Cache-aside over Redis."""
    version = await get_version(NOTES_SCOPE, owner_id)
    cache_key = _list_cache_key(owner_id, version)
    cached = await get_json(cache_key)
    if cached is not None:
        return [NoteRead.model_validate(item) for item in cached]

    result = await db.scalars(select(Note).where(Note.owner_id == owner_id))
    notes = [NoteRead.model_validate(note) for note in result]

    await set_json(cache_key, [note.model_dump(mode="json") for note in notes])
    return notes


async def get_note(db: AsyncSession, owner_id: uuid.UUID, note_id: uuid.UUID) -> NoteRead:
    """Fetch a single note by id, raising if it doesn't exist or isn't owned by the user."""
    version = await get_version(NOTES_SCOPE, owner_id)
    cache_key = _item_cache_key(owner_id, note_id, version)
    cached = await get_json(cache_key)
    if cached is not None:
        return NoteRead.model_validate(cached)

    note = NoteRead.model_validate(await _get_owned_note(db, owner_id, note_id))
    await set_json(cache_key, note.model_dump(mode="json"))
    return note


async def update_note(
    db: AsyncSession, owner_id: uuid.UUID, note_id: uuid.UUID, data: NoteUpdate
) -> Note:
    """Apply only the fields present in `data` to an existing note."""
    note = await _get_owned_note(db, owner_id, note_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(note, field, value)
    await db.commit()
    await db.refresh(note)
    await _invalidate_note_cache(owner_id)
    return note


async def delete_note(db: AsyncSession, owner_id: uuid.UUID, note_id: uuid.UUID) -> None:
    """Delete a note owned by the given user."""
    note = await _get_owned_note(db, owner_id, note_id)
    await db.delete(note)
    await db.commit()
    await _invalidate_note_cache(owner_id)
