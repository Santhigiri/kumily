"""Request/response schemas for the public application config.

Back the endpoints under ``/api/v1/settings``. Reads are public; writes
require the ``admin`` role (see ``features/settings/router.py``).

Each known ``SettingKey`` has a matching ``*Value`` model here describing the
expected shape of its ``value`` field — these are what
``features/settings/service.py`` validates a PUT's ``value`` against and
falls back to (as defaults) when no row is stored yet for that key.
"""
from __future__ import annotations

import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.utils.languages import LanguageCode


class CalendarRangeValue(BaseModel):
    """Inclusive year bounds the app supports for calendar/date pickers."""

    start_year: int = 2000
    end_year: int = 2035


class LanguagesValue(BaseModel):
    """Language codes available across Kumily's multi-language content.

    Defaults to every member of ``utils.languages.LanguageCode`` (the same
    allow-list every feature's ``language_code`` field validates against),
    so this can't silently drift from what content actually supports.
    """

    codes: List[str] = Field(
        default_factory=lambda: [c.value for c in LanguageCode]
    )


class AppSettingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    key: str
    value: dict
    description: Optional[str] = None
    updated_at: datetime.datetime
    updated_by: Optional[int] = None


class AppSettingUpdate(BaseModel):
    value: dict
    description: Optional[str] = None
