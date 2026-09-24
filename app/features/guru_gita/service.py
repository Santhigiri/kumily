"""GuruGitaService — orchestrates read/upsert/delete of Guru Gita verses.

A frozen dataclass depending on ``GuruGitaRepositoryPort`` (from
``features/guru_gita/ports.py``) and a ``UnitOfWork``, never on the concrete
adapter class. DTO -> schema conversion happens here, not in the router.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from app.core.ports.unit_of_work import UnitOfWork
from app.features.guru_gita.ports import (
    GuruGitaRepositoryPort,
    GuruGitaVerseGet,
    GuruGitaVerseNotFoundException,
)
from app.features.guru_gita.schemas import GuruGitaTranslationSchema, GuruGitaVerseDetail

GuruGitaVerseNotFound = GuruGitaVerseNotFoundException


@dataclass(frozen=True)
class GuruGitaService:
    guru_gita_repository: GuruGitaRepositoryPort
    uow: UnitOfWork

    def _verse_get_to_detail(
        self, verse: GuruGitaVerseGet, language_code: Optional[str] = None
    ) -> GuruGitaVerseDetail:
        translations = verse.translations
        if language_code is not None:
            translations = [
                t for t in translations if t.language_code == language_code
            ]
        return GuruGitaVerseDetail(
            verse_number=verse.verse_number,
            translations=[
                GuruGitaTranslationSchema(
                    language_code=t.language_code, text=t.text
                )
                for t in translations
            ],
        )

    def list_all(self, language_code: Optional[str] = None) -> List[GuruGitaVerseDetail]:
        verses = self.guru_gita_repository.list_all()
        return [self._verse_get_to_detail(v, language_code) for v in verses]

    def get(self, verse_number: int, language_code: Optional[str] = None) -> GuruGitaVerseDetail:
        verse = self.guru_gita_repository.get(verse_number)
        if verse is None:
            raise GuruGitaVerseNotFoundException(verse_number)
        return self._verse_get_to_detail(verse, language_code)

    def upsert_translation(
        self, verse_number: int, language_code: str, text: str
    ) -> GuruGitaVerseDetail:
        with self.uow as uow:
            verse = self.guru_gita_repository.upsert_translation(
                verse_number, language_code, text
            )
            uow.commit()
            return self._verse_get_to_detail(verse)

    def delete_translation(self, verse_number: int, language_code: str) -> None:
        verse = self.guru_gita_repository.get(verse_number)
        if verse is None or not any(
            t.language_code == language_code for t in verse.translations
        ):
            raise GuruGitaVerseNotFoundException(verse_number)
        with self.uow as uow:
            self.guru_gita_repository.delete_translation(verse_number, language_code)
            uow.commit()

    def delete_verse(self, verse_number: int) -> None:
        if self.guru_gita_repository.get(verse_number) is None:
            raise GuruGitaVerseNotFoundException(verse_number)
        with self.uow as uow:
            self.guru_gita_repository.delete_verse(verse_number)
            uow.commit()
