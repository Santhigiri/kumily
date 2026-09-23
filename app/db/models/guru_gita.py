from typing import Optional

from sqlmodel import Field, SQLModel, UniqueConstraint


class GuruGitaVerse(SQLModel, table=True):
    """One verse's text in one language.

    A verse "exists" only as its translation rows: ``verse_number`` is shared
    across every language row for that verse, and there is no separate parent
    row to create first. Adding a new language later is purely inserting more
    rows under a new ``language_code`` — no schema migration needed.
    """

    __tablename__ = "guru_gita_verse"  # pyright: ignore[reportAssignmentType]
    __table_args__ = (
        UniqueConstraint("verse_number", "language_code", name="uq_guru_gita_verse_number_language"),
    )

    id:            Optional[int] = Field(default=None, primary_key=True)
    verse_number:  int = Field(index=True)
    language_code: str = Field(index=True)
    text:          str
