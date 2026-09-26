"""drop app_setting table

Revision ID: 49f24ac5d952
Revises: c1a2b3d4e5f6
Create Date: 2026-09-26 00:00:01.000000

The public application settings feature (c1a2b3d4e5f6) was reverted before
release. That revert deleted the feature's code and migration file outright
instead of reversing the migration, which left any database that had
already run ``alembic upgrade head`` while the feature was merged stamped
at a revision id (``c1a2b3d4e5f6``) no longer present in the codebase,
breaking ``alembic upgrade head`` for it (``Can't locate revision``).

c1a2b3d4e5f6 has been restored verbatim as a real link in the migration
chain so those databases can resolve their current revision, and this
migration now formally reverses it by dropping ``app_setting`` — matching
the feature's removal from the code.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes
import app.db.models.types


# revision identifiers, used by Alembic.
revision: str = '49f24ac5d952'
down_revision: Union[str, Sequence[str], None] = 'c1a2b3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop the app_setting table (reverted feature)."""
    op.drop_table('app_setting')


def downgrade() -> None:
    """Recreate the app_setting table."""
    op.create_table('app_setting',
    sa.Column('key', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('value', sa.JSON(), nullable=False),
    sa.Column('description', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('updated_at', app.db.models.types.UTCDateTime(timezone=True), nullable=False),
    sa.Column('updated_by', sa.Integer(), nullable=True),
    sa.PrimaryKeyConstraint('key')
    )
