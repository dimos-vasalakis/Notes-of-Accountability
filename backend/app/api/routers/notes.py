import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models.note import Note
from app.models.user import User
from app.schemas.note import NoteCreate, NoteRead, NoteUpdate
from app.services import note_service

router = APIRouter(prefix="/api/notes", tags=["notes"])


@router.post("", response_model=NoteRead, status_code=status.HTTP_201_CREATED)
async def create_note(
    data: NoteCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Note:
    return await note_service.create_note(db, current_user.id, data)


@router.get("", response_model=list[NoteRead])
async def list_notes(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Note]:
    return await note_service.list_notes(db, current_user.id)


@router.get("/{note_id}", response_model=NoteRead)
async def get_note(
    note_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Note:
    return await note_service.get_note(db, current_user.id, note_id)


@router.patch("/{note_id}", response_model=NoteRead)
async def update_note(
    note_id: uuid.UUID,
    data: NoteUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Note:
    return await note_service.update_note(db, current_user.id, note_id, data)


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(
    note_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await note_service.delete_note(db, current_user.id, note_id)
