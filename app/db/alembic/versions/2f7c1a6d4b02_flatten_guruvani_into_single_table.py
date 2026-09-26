"""flatten guruvani into a single translation table

Revision ID: 2f7c1a6d4b02
Revises: 9363bde18594
Create Date: 2026-09-26 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision: str = '2f7c1a6d4b02'
down_revision: Union[str, Sequence[str], None] = '9363bde18594'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.

    Drops the ``guruvani`` parent table and folds its ``sort_order`` into
    ``guruvani_translation`` directly, duplicated across every language row
    sharing a ``quote_id`` — matching ``guru_gita_verse``'s single-table
    shape. ``guruvani_translation.guruvani_id`` is renamed to ``quote_id`` and
    its foreign key to ``guruvani.id`` is dropped: a quote's identity is now a
    plain grouping key, not a reference to any other table.
    """
    op.add_column(
        'guruvani_translation', sa.Column('sort_order', sa.Integer(), nullable=True)
    )
    op.execute(
        "UPDATE guruvani_translation SET sort_order = ("
        "SELECT guruvani.sort_order FROM guruvani "
        "WHERE guruvani.id = guruvani_translation.guruvani_id"
        ")"
    )
    op.alter_column('guruvani_translation', 'sort_order', nullable=False)
    op.create_index(
        op.f('ix_guruvani_translation_sort_order'), 'guruvani_translation', ['sort_order'], unique=False
    )

    with op.batch_alter_table('guruvani_translation') as batch_op:
        batch_op.drop_constraint(
            'uq_guruvani_translation_guruvani_language', type_='unique'
        )
        batch_op.drop_constraint(
            'guruvani_translation_guruvani_id_fkey', type_='foreignkey'
        )
        batch_op.alter_column('guruvani_id', new_column_name='quote_id')
        batch_op.create_unique_constraint(
            'uq_guruvani_translation_quote_language', ['quote_id', 'language_code']
        )

    op.drop_index('ix_guruvani_translation_guruvani_id', table_name='guruvani_translation')
    op.create_index(
        op.f('ix_guruvani_translation_quote_id'), 'guruvani_translation', ['quote_id'], unique=False
    )

    op.drop_table('guruvani')


def downgrade() -> None:
    """Downgrade schema.

    Recreates the ``guruvani`` parent table, backfilling it from one row per
    distinct ``quote_id`` (its ``sort_order``, taken from any of its
    language rows since the upgrade duplicated it across all of them), then
    restores ``guruvani_translation.guruvani_id`` as a foreign key back to it
    and drops the now-redundant ``sort_order`` column from the translation
    table.
    """
    op.create_table(
        'guruvani',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_guruvani_sort_order'), 'guruvani', ['sort_order'], unique=False)

    op.execute(
        "INSERT INTO guruvani (id, sort_order) "
        "SELECT DISTINCT quote_id, sort_order FROM guruvani_translation"
    )

    with op.batch_alter_table('guruvani_translation') as batch_op:
        batch_op.drop_constraint(
            'uq_guruvani_translation_quote_language', type_='unique'
        )
        batch_op.alter_column('quote_id', new_column_name='guruvani_id')
        batch_op.create_foreign_key(
            'guruvani_translation_guruvani_id_fkey', 'guruvani', ['guruvani_id'], ['id']
        )
        batch_op.create_unique_constraint(
            'uq_guruvani_translation_guruvani_language', ['guruvani_id', 'language_code']
        )

    op.drop_index(op.f('ix_guruvani_translation_quote_id'), table_name='guruvani_translation')
    op.create_index(
        op.f('ix_guruvani_translation_guruvani_id'), 'guruvani_translation', ['guruvani_id'], unique=False
    )

    op.drop_index(op.f('ix_guruvani_translation_sort_order'), table_name='guruvani_translation')
    op.drop_column('guruvani_translation', 'sort_order')
