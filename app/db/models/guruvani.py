from typing import Optional

from sqlmodel import Field, SQLModel, UniqueConstraint


class Guruvani(SQLModel, table=True):
    """A single quote's identity and display order. Text lives in GuruvaniTranslation."""

    __tablename__ = "guruvani"  # pyright: ignore[reportAssignmentType]

    id:         Optional[int] = Field(default=None, primary_key=True)
    sort_order: int = Field(index=True)


class GuruvaniTranslation(SQLModel, table=True):
    """One quote's text in one language.

    A quote "exists" as a ``Guruvani`` parent row (identity + ``sort_order``)
    plus its translation rows; adding a new language later is purely
    inserting more rows under a new ``language_code`` — no schema migration
    needed.
    """

    __tablename__ = "guruvani_translation"  # pyright: ignore[reportAssignmentType]
    __table_args__ = (
        UniqueConstraint(
            "guruvani_id", "language_code", name="uq_guruvani_translation_guruvani_language"
        ),
    )

    id:            Optional[int] = Field(default=None, primary_key=True)
    guruvani_id:   int = Field(index=True, foreign_key="guruvani.id")
    language_code: str = Field(index=True)
    text:          str
