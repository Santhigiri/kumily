"""
Known ``app_setting`` keys.

A plain string ``Enum`` (mirrors ``utils.roles.Role``) so call sites reference
a named constant instead of a magic string. Each member's value shape is
defined by the matching Pydantic model in ``features/settings/schemas.py``.
"""
from __future__ import annotations

from enum import Enum


class SettingKey(str, Enum):
    CALENDAR_RANGE = "calendar_range"
    LANGUAGES = "languages"
