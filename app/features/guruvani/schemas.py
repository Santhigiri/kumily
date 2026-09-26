"""Request/response schemas for the editable Guruvani quotes.

Back the endpoints under ``/api/v1/guruvani``. Reads are public; writes
require the ``admin`` role (see ``features/guruvani/router.py``).
"""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.utils.languages import LanguageCode


class GuruvaniTranslationSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    language_code: LanguageCode
    text: str = Field(min_length=1)


class GuruvaniDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sort_order: int
    translations: List[GuruvaniTranslationSchema]


class GuruvaniCreate(BaseModel):
    """Body for creating a new quote. A quote exists only via its translation
    rows, so creation requires the first translation up front."""

    sort_order: Optional[int] = Field(
        default=None,
        description="Display order; assigned automatically when omitted.",
    )
    language_code: LanguageCode
    text: str = Field(min_length=1)


class GuruvaniTranslationUpsert(BaseModel):
    """Body for creating or updating one language's text for a quote.

    ``guruvani_id`` and ``language_code`` come from the URL path.
    """

    text: str = Field(min_length=1)


class GuruvaniSortOrderUpdate(BaseModel):
    sort_order: int
