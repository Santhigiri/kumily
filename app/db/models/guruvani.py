from typing import Optional

from sqlmodel import Field, SQLModel, UniqueConstraint


class GuruvaniTranslation(SQLModel, table=True):
    """One quote's text in one language.

    A quote "exists" only as its translation rows: ``quote_id`` and
    ``sort_order`` are duplicated across every language row sharing that
    ``quote_id`` — there is no separate parent table, matching
    ``guru_gita_verse``'s shape. Unlike Guru Gita's ``verse_number``, a quote
    has no natural external identity, so ``quote_id`` is a plain grouping key
    (not a foreign key) assigned from the current max value on create.
    """

    __tablename__ = "guruvani_translation"  # pyright: ignore[reportAssignmentType]
    __table_args__ = (
        UniqueConstraint(
            "quote_id", "language_code", name="uq_guruvani_translation_quote_language"
        ),
    )

    id:            Optional[int] = Field(default=None, primary_key=True)
    quote_id:      int = Field(index=True)
    language_code: str = Field(index=True)
    text:          str
    sort_order:    int = Field(index=True)
