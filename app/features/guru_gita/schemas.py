"""Request/response schemas for the editable Guru Gita verses.

Back the endpoints under ``/api/v1/guru-gita``. Reads are public; writes
require the ``admin`` role (see ``features/guru_gita/router.py``).
"""
from __future__ import annotations

from typing import List

from pydantic import BaseModel, ConfigDict, Field

from app.utils.languages import LanguageCode


class GuruGitaTranslationSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    language_code: LanguageCode
    text: str = Field(min_length=1)


class GuruGitaVerseDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    verse_number: int
    translations: List[GuruGitaTranslationSchema]


class GuruGitaTranslationUpsert(BaseModel):
    """Body for creating or updating one language's text for a verse.

    ``verse_number`` and ``language_code`` come from the URL path.
    """

    text: str = Field(min_length=1)
