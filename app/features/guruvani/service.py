"""GuruvaniService — orchestrates create/read/upsert/delete of Guruvani quotes.

A frozen dataclass depending on ``GuruvaniRepositoryPort`` (from
``features/guruvani/ports.py``) and a ``UnitOfWork``, never on the concrete
adapter class. DTO -> schema conversion happens here, not in the router.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from app.core.ports.unit_of_work import UnitOfWork
from app.features.guruvani.ports import (
    GuruvaniGet,
    GuruvaniNotFoundException,
    GuruvaniRepositoryPort,
)
from app.features.guruvani.schemas import GuruvaniDetail, GuruvaniTranslationSchema

GuruvaniNotFound = GuruvaniNotFoundException


@dataclass(frozen=True)
class GuruvaniService:
    guruvani_repository: GuruvaniRepositoryPort
    uow: UnitOfWork

    def _guruvani_get_to_detail(
        self, quote: GuruvaniGet, language_code: Optional[str] = None
    ) -> GuruvaniDetail:
        translations = quote.translations
        if language_code is not None:
            translations = [
                t for t in translations if t.language_code == language_code
            ]
        return GuruvaniDetail(
            id=quote.id,
            sort_order=quote.sort_order,
            translations=[
                GuruvaniTranslationSchema(language_code=t.language_code, text=t.text)
                for t in translations
            ],
        )

    def list_all(self, language_code: Optional[str] = None) -> List[GuruvaniDetail]:
        quotes = self.guruvani_repository.list_all()
        return [self._guruvani_get_to_detail(q, language_code) for q in quotes]

    def get(self, guruvani_id: int, language_code: Optional[str] = None) -> GuruvaniDetail:
        quote = self.guruvani_repository.get(guruvani_id)
        if quote is None:
            raise GuruvaniNotFoundException(guruvani_id)
        return self._guruvani_get_to_detail(quote, language_code)

    def get_random(self, language_code: Optional[str] = None) -> GuruvaniDetail:
        quote = self.guruvani_repository.get_random()
        if quote is None:
            raise GuruvaniNotFoundException("no Guruvani entries exist")
        return self._guruvani_get_to_detail(quote, language_code)

    def create(self, sort_order: Optional[int]) -> GuruvaniDetail:
        with self.uow as uow:
            quote = self.guruvani_repository.create(sort_order)
            uow.commit()
            return self._guruvani_get_to_detail(quote)

    def upsert_translation(
        self, guruvani_id: int, language_code: str, text: str
    ) -> GuruvaniDetail:
        if self.guruvani_repository.get(guruvani_id) is None:
            raise GuruvaniNotFoundException(guruvani_id)
        with self.uow as uow:
            quote = self.guruvani_repository.upsert_translation(
                guruvani_id, language_code, text
            )
            uow.commit()
            return self._guruvani_get_to_detail(quote)

    def delete_translation(self, guruvani_id: int, language_code: str) -> None:
        quote = self.guruvani_repository.get(guruvani_id)
        if quote is None or not any(
            t.language_code == language_code for t in quote.translations
        ):
            raise GuruvaniNotFoundException(guruvani_id)
        with self.uow as uow:
            self.guruvani_repository.delete_translation(guruvani_id, language_code)
            uow.commit()

    def update_sort_order(self, guruvani_id: int, sort_order: int) -> GuruvaniDetail:
        if self.guruvani_repository.get(guruvani_id) is None:
            raise GuruvaniNotFoundException(guruvani_id)
        with self.uow as uow:
            quote = self.guruvani_repository.update_sort_order(guruvani_id, sort_order)
            uow.commit()
            return self._guruvani_get_to_detail(quote)

    def delete(self, guruvani_id: int) -> None:
        if self.guruvani_repository.get(guruvani_id) is None:
            raise GuruvaniNotFoundException(guruvani_id)
        with self.uow as uow:
            self.guruvani_repository.delete(guruvani_id)
            uow.commit()
