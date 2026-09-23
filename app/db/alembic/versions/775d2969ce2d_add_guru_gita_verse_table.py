"""add guru_gita_verse table

Revision ID: 775d2969ce2d
Revises: 4101b960b879
Create Date: 2026-09-23 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision: str = '775d2969ce2d'
down_revision: Union[str, Sequence[str], None] = '4101b960b879'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('guru_gita_verse',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('verse_number', sa.Integer(), nullable=False),
    sa.Column('language_code', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('text', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('verse_number', 'language_code', name='uq_guru_gita_verse_number_language')
    )
    op.create_index(op.f('ix_guru_gita_verse_language_code'), 'guru_gita_verse', ['language_code'], unique=False)
    op.create_index(op.f('ix_guru_gita_verse_verse_number'), 'guru_gita_verse', ['verse_number'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_guru_gita_verse_verse_number'), table_name='guru_gita_verse')
    op.drop_index(op.f('ix_guru_gita_verse_language_code'), table_name='guru_gita_verse')
    op.drop_table('guru_gita_verse')
