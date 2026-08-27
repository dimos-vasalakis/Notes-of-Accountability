"""add accountability pods

Revision ID: d4b8e0c5711f
Revises: c1a7d3f90b21
Create Date: 2026-08-27 10:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4b8e0c5711f'
down_revision: Union[str, Sequence[str], None] = 'c1a7d3f90b21'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'pods',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('invite_code', sa.String(length=12), nullable=False),
        sa.Column('owner_id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_pods_invite_code'), 'pods', ['invite_code'], unique=True)
    op.create_index(op.f('ix_pods_owner_id'), 'pods', ['owner_id'])

    op.create_table(
        'pod_memberships',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('pod_id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('joined_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('last_nudge_sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['pod_id'], ['pods.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('pod_id', 'user_id', name='uq_pod_membership'),
    )
    op.create_index(op.f('ix_pod_memberships_pod_id'), 'pod_memberships', ['pod_id'])
    op.create_index(op.f('ix_pod_memberships_user_id'), 'pod_memberships', ['user_id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_pod_memberships_user_id'), table_name='pod_memberships')
    op.drop_index(op.f('ix_pod_memberships_pod_id'), table_name='pod_memberships')
    op.drop_table('pod_memberships')
    op.drop_index(op.f('ix_pods_owner_id'), table_name='pods')
    op.drop_index(op.f('ix_pods_invite_code'), table_name='pods')
    op.drop_table('pods')
