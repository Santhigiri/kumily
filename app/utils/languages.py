"""
Supported language codes for translatable content.

``LanguageCode`` is a string enum so it serialises naturally in JSON
responses and can be used directly as a Pydantic field type. It is the
single allow-list every content feature's ``schemas.py`` validates
``language_code`` against at the HTTP boundary — ``ports.py``, repositories,
and DB models keep ``language_code`` as a plain ``str`` (validation happens
once, here, not duplicated across layers).
"""
from __future__ import annotations

from enum import Enum


class LanguageCode(str, Enum):
    EN = "en"
    ML = "ml"
