"""
GuruvaniRepository — concrete adapter for ``GuruvaniRepositoryPort``, CRUD for
the ``guruvani``/``guruvani_translation`` tables against SQLModel.

Every quote is a ``Guruvani`` parent row (identity + ``sort_order``) plus its
``GuruvaniTranslation`` rows, one per language. Mutating methods do NOT
commit — the caller (``features.guruvani.service``) owns the transaction.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from sqlalchemy import func
from sqlmodel import Session, select

from app.db.models.guruvani import Guruvani as GuruvaniRow
from app.db.models.guruvani import GuruvaniTranslation as GuruvaniTranslationRow
from app.db.typing_utils import col
from app.features.guruvani.ports import GuruvaniGet, GuruvaniTranslation


@dataclass()
class GuruvaniRepository:
    _s: Session

    def _rows_to_guruvani_get(
        self, parent: GuruvaniRow, translation_rows: List[GuruvaniTranslationRow]
    ) -> GuruvaniGet:
        assert parent.id is not None
        return GuruvaniGet(
            id=parent.id,
            sort_order=parent.sort_order,
            translations=[
                GuruvaniTranslation(language_code=row.language_code, text=row.text)
                for row in translation_rows
            ],
        )

    def _translations_for(self, guruvani_id: int) -> List[GuruvaniTranslationRow]:
        return list(
            self._s.exec(
                select(GuruvaniTranslationRow)
                .where(col(GuruvaniTranslationRow.guruvani_id) == guruvani_id)
                .order_by(col(GuruvaniTranslationRow.language_code))
            ).all()
        )

    # ── Getters ────────────────────────────────────────────────────────────────

    def get(self, guruvani_id: int) -> Optional[GuruvaniGet]:
        parent = self._s.get(GuruvaniRow, guruvani_id)
        if parent is None:
            return None
        return self._rows_to_guruvani_get(parent, self._translations_for(guruvani_id))

    def list_all(self) -> List[GuruvaniGet]:
        parents = self._s.exec(
            select(GuruvaniRow).order_by(col(GuruvaniRow.sort_order))
        ).all()
        return [
            self._rows_to_guruvani_get(parent, self._translations_for(parent.id))
            for parent in parents
            if parent.id is not None
        ]

    def get_random(self) -> Optional[GuruvaniGet]:
        """One quote picked at random, or None if none exist.

        ``func.random()`` is the SQL standard name for this and works
        identically on both Postgres and SQLite (the test suite's engine).
        """
        parent = self._s.exec(
            select(GuruvaniRow).order_by(func.random()).limit(1)
        ).first()
        if parent is None:
            return None
        return self._rows_to_guruvani_get(parent, self._translations_for(parent.id))

    # ── Setters ────────────────────────────────────────────────────────────────

    def create(self, sort_order: Optional[int]) -> GuruvaniGet:
        """Insert a new quote's parent row (no translations yet). Does NOT commit."""
        parent = GuruvaniRow(
            sort_order=sort_order if sort_order is not None else self._next_sort_order()
        )
        self._s.add(parent)
        self._s.flush()
        return self._rows_to_guruvani_get(parent, [])

    def upsert_translation(
        self, guruvani_id: int, language_code: str, text: str
    ) -> GuruvaniGet:
        """Create or update the row for *(guruvani_id, language_code)*. Does NOT commit."""
        row = self._get_translation_row(guruvani_id, language_code)
        if row is None:
            row = GuruvaniTranslationRow(
                guruvani_id=guruvani_id, language_code=language_code, text=text
            )
        else:
            row.text = text
        self._s.add(row)
        self._s.flush()

        quote = self.get(guruvani_id)
        assert quote is not None
        return quote

    def delete_translation(self, guruvani_id: int, language_code: str) -> None:
        row = self._get_translation_row(guruvani_id, language_code)
        assert row is not None
        self._s.delete(row)
        self._s.flush()

    def update_sort_order(self, guruvani_id: int, sort_order: int) -> GuruvaniGet:
        parent = self._s.get(GuruvaniRow, guruvani_id)
        assert parent is not None
        parent.sort_order = sort_order
        self._s.add(parent)
        self._s.flush()
        return self._rows_to_guruvani_get(parent, self._translations_for(guruvani_id))

    def delete(self, guruvani_id: int) -> None:
        parent = self._s.get(GuruvaniRow, guruvani_id)
        assert parent is not None
        for row in self._translations_for(guruvani_id):
            self._s.delete(row)
        self._s.flush()
        self._s.delete(parent)
        self._s.flush()

    # ── Private helpers ─────────────────────────────────────────────────────────

    def _get_translation_row(
        self, guruvani_id: int, language_code: str
    ) -> Optional[GuruvaniTranslationRow]:
        return self._s.exec(
            select(GuruvaniTranslationRow).where(
                col(GuruvaniTranslationRow.guruvani_id) == guruvani_id,
                col(GuruvaniTranslationRow.language_code) == language_code,
            )
        ).first()

    def _next_sort_order(self) -> int:
        current_max = self._s.exec(select(func.max(GuruvaniRow.sort_order))).first()
        return (current_max or 0) + 1
