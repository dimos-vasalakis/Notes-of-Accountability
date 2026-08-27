"""add student mode and exam prep

Revision ID: c1a7d3f90b21
Revises: 5552e04fb75a
Create Date: 2026-08-27 10:00:00.000000

"""
import uuid
from datetime import date
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c1a7d3f90b21'
down_revision: Union[str, Sequence[str], None] = '5552e04fb75a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ---------------------------------------------------------------------------
# Seed data for the Group D (Οικονομίας & Πληροφορικής) orientation track.
#
# !! PLACEHOLDER VALUES !!
# `weight_coefficient` and `exam_date` below are NOT verified. Panhellenic
# subject coefficients and exam dates are set each year by ministry decision
# (ΦΕΚ) and change between years and between scientific fields (επιστημονικά
# πεδία). Verify against the current-year decision and correct them via
# backend/scripts/seed_exam_config.py before any student plans around them.
# ---------------------------------------------------------------------------
_TRACK = "group_d"
_ACADEMIC_YEAR = "2026-2027"
_PLACEHOLDER_EXAM_DATE = date(2027, 6, 1)

_SUBJECTS = [
    # (code, name_el, name_en, placeholder weight, display_order)
    ("neoelliniki", "Νεοελληνική Γλώσσα και Λογοτεχνία", "Modern Greek Language and Literature", 1.0, 1),
    ("mathimatika", "Μαθηματικά", "Mathematics", 1.3, 2),
    ("aepp", "Ανάπτυξη Εφαρμογών σε Προγραμματιστικό Περιβάλλον", "Application Development in a Programming Environment", 1.3, 3),
    ("aoth", "Αρχές Οικονομικής Θεωρίας", "Principles of Economic Theory", 1.0, 4),
]


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'users',
        sa.Column('is_student', sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column('users', sa.Column('exam_track', sa.String(length=32), nullable=True))
    op.add_column('users', sa.Column('display_name', sa.String(length=64), nullable=True))
    op.add_column('tasks', sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True))
    # Backfill already-finished tasks, otherwise every existing user's streak
    # reads 0 on the day this ships. `updated_at` is the closest available
    # proxy for when the task was completed.
    # NOTE: the status enum is stored by NAME ('DONE'), not value ('done').
    op.execute(
        "UPDATE tasks SET completed_at = updated_at WHERE status = 'DONE'"
    )

    exam_subjects = op.create_table(
        'exam_subjects',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('track', sa.String(length=32), nullable=False),
        sa.Column('code', sa.String(length=64), nullable=False),
        sa.Column('name_el', sa.String(length=128), nullable=False),
        sa.Column('name_en', sa.String(length=128), nullable=False),
        sa.Column('weight_coefficient', sa.Float(), nullable=False),
        sa.Column('display_order', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_exam_subjects_track'), 'exam_subjects', ['track'])
    op.create_index(op.f('ix_exam_subjects_code'), 'exam_subjects', ['code'], unique=True)

    exam_configs = op.create_table(
        'exam_configs',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('track', sa.String(length=32), nullable=False),
        sa.Column('academic_year', sa.String(length=16), nullable=False),
        sa.Column('exam_date', sa.Date(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_exam_configs_track'), 'exam_configs', ['track'], unique=True)

    op.create_table(
        'study_sessions',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('owner_id', sa.Uuid(), nullable=False),
        sa.Column('subject_code', sa.String(length=64), nullable=True),
        sa.Column('duration_seconds', sa.Integer(), nullable=False),
        sa.Column(
            'source',
            sa.Enum('FOCUS_TIMER', 'MANUAL', name='studysessionsource', native_enum=False, length=20),
            nullable=False,
        ),
        sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_study_sessions_owner_id'), 'study_sessions', ['owner_id'])
    op.create_index(op.f('ix_study_sessions_subject_code'), 'study_sessions', ['subject_code'])
    op.create_index(op.f('ix_study_sessions_occurred_at'), 'study_sessions', ['occurred_at'])

    # Seed here so the DB is usable straight after migrating; re-edit later
    # with backend/scripts/seed_exam_config.py rather than a new migration.
    op.bulk_insert(
        exam_subjects,
        [
            {
                "id": uuid.uuid4(),
                "track": _TRACK,
                "code": code,
                "name_el": name_el,
                "name_en": name_en,
                "weight_coefficient": weight,
                "display_order": order,
                "is_active": True,
            }
            for code, name_el, name_en, weight, order in _SUBJECTS
        ],
    )
    op.bulk_insert(
        exam_configs,
        [
            {
                "id": uuid.uuid4(),
                "track": _TRACK,
                "academic_year": _ACADEMIC_YEAR,
                "exam_date": _PLACEHOLDER_EXAM_DATE,
                "is_active": True,
            }
        ],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_study_sessions_occurred_at'), table_name='study_sessions')
    op.drop_index(op.f('ix_study_sessions_subject_code'), table_name='study_sessions')
    op.drop_index(op.f('ix_study_sessions_owner_id'), table_name='study_sessions')
    op.drop_table('study_sessions')
    op.drop_index(op.f('ix_exam_configs_track'), table_name='exam_configs')
    op.drop_table('exam_configs')
    op.drop_index(op.f('ix_exam_subjects_code'), table_name='exam_subjects')
    op.drop_index(op.f('ix_exam_subjects_track'), table_name='exam_subjects')
    op.drop_table('exam_subjects')
    op.drop_column('tasks', 'completed_at')
    op.drop_column('users', 'display_name')
    op.drop_column('users', 'exam_track')
    op.drop_column('users', 'is_student')
