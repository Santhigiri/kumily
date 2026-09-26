import datetime
from typing import Optional

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from app.db.models.types import UTCDateTime


class AppSetting(SQLModel, table=True):
    """A single publicly-readable, admin-editable application setting.

    Keyed by a stable string (see ``utils.settings_keys.SettingKey``); the
    shape of ``value`` is defined per-key by a Pydantic model in
    ``features/settings/schemas.py``.
    """

    __tablename__ = "app_setting"  # pyright: ignore[reportAssignmentType]

    key:         str                       = Field(primary_key=True)
    value:       dict                      = Field(sa_column=Column(JSON, nullable=False))
    description: Optional[str]             = None
    updated_at:  datetime.datetime         = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc),
        sa_column=Column(UTCDateTime, nullable=False),
    )
    updated_by:  Optional[int]             = None
