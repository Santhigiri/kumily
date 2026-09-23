"""
GuruGitaRepository — concrete adapter for ``GuruGitaRepositoryPort``, CRUD for
the ``guru_gita_verse`` table against SQLModel.

Every row is a single ``(verse_number, language_code)`` translation; a verse
"exists" only through its rows, grouped into a ``GuruGitaVerseGet`` here.
Mutating methods do NOT commit — the caller (``features.guru_gita.service``)
owns the transaction.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from sqlmodel import Session, select

from app.db.models.guru_gita import GuruGitaVerse as GuruGitaVerseRow
from app.db.typing_utils import col
from app.features.guru_gita.ports import GuruGitaTranslation, GuruGitaVerseGet


@dataclass()
class GuruGitaRepository:
    _s: Session

    def _rows_to_verse_get(
        self, verse_number: int, rows: List[GuruGitaVerseRow]
    ) -> GuruGitaVerseGet:
        return GuruGitaVerseGet(
            verse_number=verse_number,
            translations=[
                GuruGitaTranslation(language_code=row.language_code, text=row.text)
                for row in rows
            ],
        )

    # ── Getters ────────────────────────────────────────────────────────────────

    def get(self, verse_number: int) -> Optional[GuruGitaVerseGet]:
        rows = self._s.exec(
            select(GuruGitaVerseRow)
            .where(col(GuruGitaVerseRow.verse_number) == verse_number)
            .order_by(col(GuruGitaVerseRow.language_code))
        ).all()
        if not rows:
            return None
        return self._rows_to_verse_get(verse_number, list(rows))

    def list_all(self) -> List[GuruGitaVerseGet]:
        rows = self._s.exec(
            select(GuruGitaVerseRow).order_by(
                col(GuruGitaVerseRow.verse_number), col(GuruGitaVerseRow.language_code)
            )
        ).all()

        verses: List[GuruGitaVerseGet] = []
        current_number: Optional[int] = None
        current_rows: List[GuruGitaVerseRow] = []
        for row in rows:
            if row.verse_number != current_number:
                if current_number is not None:
                    verses.append(self._rows_to_verse_get(current_number, current_rows))
                current_number = row.verse_number
                current_rows = []
            current_rows.append(row)
        if current_number is not None:
            verses.append(self._rows_to_verse_get(current_number, current_rows))

        return verses

    def _get_translation_row(
        self, verse_number: int, language_code: str
    ) -> Optional[GuruGitaVerseRow]:
        return self._s.exec(
            select(GuruGitaVerseRow).where(
                col(GuruGitaVerseRow.verse_number) == verse_number,
                col(GuruGitaVerseRow.language_code) == language_code,
            )
        ).first()

    # ── Setters ────────────────────────────────────────────────────────────────

    def upsert_translation(
        self, verse_number: int, language_code: str, text: str
    ) -> GuruGitaVerseGet:
        """Create or update the row for *(verse_number, language_code)*. Does NOT commit."""
        row = self._get_translation_row(verse_number, language_code)
        if row is None:
            row = GuruGitaVerseRow(
                verse_number=verse_number, language_code=language_code, text=text
            )
        else:
            row.text = text
        self._s.add(row)
        self._s.flush()

        verse = self.get(verse_number)
        assert verse is not None
        return verse

    def delete_translation(self, verse_number: int, language_code: str) -> None:
        row = self._get_translation_row(verse_number, language_code)
        assert row is not None
        self._s.delete(row)
        self._s.flush()

    def delete_verse(self, verse_number: int) -> None:
        rows = self._s.exec(
            select(GuruGitaVerseRow).where(
                col(GuruGitaVerseRow.verse_number) == verse_number
            )
        ).all()
        for row in rows:
            self._s.delete(row)
        self._s.flush()
