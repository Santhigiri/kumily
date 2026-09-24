"""normalize guruvani into translation rows

Revision ID: 9363bde18594
Revises: 775d2969ce2d
Create Date: 2026-09-24 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision: str = '9363bde18594'
down_revision: Union[str, Sequence[str], None] = '775d2969ce2d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.

    Splits Guruvani's fixed ``text_en``/``text_ml`` columns into a
    ``guruvani_translation`` table with one row per (guruvani_id,
    language_code) — matching ``guru_gita_verse``'s shape, so adding a
    language no longer requires a schema migration. Existing rows are
    backfilled into ``en``/``ml`` translation rows before the old columns are
    dropped.
    """
    op.create_table('guruvani_translation',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('guruvani_id', sa.Integer(), nullable=False),
    sa.Column('language_code', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('text', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.ForeignKeyConstraint(['guruvani_id'], ['guruvani.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('guruvani_id', 'language_code', name='uq_guruvani_translation_guruvani_language')
    )
    op.create_index(op.f('ix_guruvani_translation_guruvani_id'), 'guruvani_translation', ['guruvani_id'], unique=False)
    op.create_index(op.f('ix_guruvani_translation_language_code'), 'guruvani_translation', ['language_code'], unique=False)

    op.execute(
        "INSERT INTO guruvani_translation (guruvani_id, language_code, text) "
        "SELECT id, 'en', text_en FROM guruvani"
    )
    op.execute(
        "INSERT INTO guruvani_translation (guruvani_id, language_code, text) "
        "SELECT id, 'ml', text_ml FROM guruvani"
    )

    op.drop_column('guruvani', 'text_en')
    op.drop_column('guruvani', 'text_ml')


def downgrade() -> None:
    """Downgrade schema.

    Recreates ``text_en``/``text_ml``, backfills them from the ``en``/``ml``
    translation rows, then drops ``guruvani_translation``. Any language other
    than ``en``/``ml`` that was added after the upgrade is lost — this
    downgrade only reverses what the upgrade itself did.
    """
    op.add_column('guruvani', sa.Column('text_en', sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    op.add_column('guruvani', sa.Column('text_ml', sqlmodel.sql.sqltypes.AutoString(), nullable=True))

    op.execute(
        "UPDATE guruvani SET text_en = ("
        "SELECT text FROM guruvani_translation "
        "WHERE guruvani_translation.guruvani_id = guruvani.id AND guruvani_translation.language_code = 'en'"
        ")"
    )
    op.execute(
        "UPDATE guruvani SET text_ml = ("
        "SELECT text FROM guruvani_translation "
        "WHERE guruvani_translation.guruvani_id = guruvani.id AND guruvani_translation.language_code = 'ml'"
        ")"
    )

    op.alter_column('guruvani', 'text_en', nullable=False)
    op.alter_column('guruvani', 'text_ml', nullable=False)

    op.drop_index(op.f('ix_guruvani_translation_language_code'), table_name='guruvani_translation')
    op.drop_index(op.f('ix_guruvani_translation_guruvani_id'), table_name='guruvani_translation')
    op.drop_table('guruvani_translation')
